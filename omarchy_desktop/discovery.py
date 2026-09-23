"""Bounded, read-only discovery. Never execute session entries or shell commands."""
import configparser
import os
from pathlib import Path
import shlex

DESKTOPS = {
    "kde": ("KDE Plasma", ("kde", "plasma")),
    "gnome": ("GNOME", ("gnome",)),
    "xfce": ("Xfce", ("xfce",)),
    "cinnamon": ("Cinnamon", ("cinnamon",)),
    "cosmic": ("COSMIC", ("cosmic",)),
    "lxqt": ("LXQt", ("lxqt",)),
    "mate": ("MATE", ("mate",)),
    "budgie": ("Budgie", ("budgie",)),
    "deepin": ("Deepin", ("deepin",)),
    "lxde": ("LXDE", ("lxde",)),
    "enlightenment": ("Enlightenment", ("enlightenment",)),
    "sway": ("Sway", ("sway",)),
    "niri": ("Niri", ("niri",)),
    "i3": ("i3", ("i3",)),
    "openbox": ("Openbox", ("openbox",)),
    "hyprland": ("Hyprland", ("hyprland",)),
}
MAX_BYTES = 256 * 1024


class Reader:
    def __init__(self, root="/"):
        self.root = Path(root).resolve()
        self.warnings = []

    def path(self, path):
        result = self.root / str(path).lstrip("/")
        # Fixtures must never follow a symlink outside their sandbox.
        if self.root != Path("/") and not result.resolve().is_relative_to(self.root):
            raise ValueError("path escapes inspection root")
        return result

    def read(self, path):
        try:
            p = self.path(path)
            if not p.exists():
                return None
            with p.open("rb") as handle:
                raw = handle.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("file exceeds read limit")
            return raw.decode("utf-8")
        except (OSError, ValueError, UnicodeError) as exc:
            self.warnings.append(f"Cannot read {path}: {type(exc).__name__}")
            return None

    def glob(self, directory, pattern):
        try:
            return ["/" + str(p.relative_to(self.root)) for p in
                    sorted(self.path(directory).glob(pattern))]
        except (OSError, ValueError):
            self.warnings.append(f"Cannot list {directory}")
            return []

    def ini(self, path):
        text = self.read(path)
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        parser.optionxform = str
        if text is not None:
            try:
                parser.read_string(text)
            except configparser.Error:
                self.warnings.append(f"Malformed configuration: {path}")
                return None
        return parser if text is not None else None

    def executable(self, command, search_path):
        if not command:
            return False
        candidates = [command] if command.startswith("/") else [
            f"{directory}/{command}" for directory in search_path.split(":")
            if directory.startswith("/")]
        for candidate in candidates:
            try:
                p = self.path(candidate)
                if p.is_file() and os.access(p, os.X_OK):
                    return True
            except (OSError, ValueError):
                continue
        return False


def discover(root="/", environ=None):
    r = Reader(root)
    env = (os.environ if r.root == Path("/") else {}) if environ is None else environ
    settings = {}
    sources = []
    for directory in ("/usr/lib/sddm/sddm.conf.d", "/etc/sddm.conf.d"):
        sources.extend(r.glob(directory, "*.conf"))
    sources.append("/etc/sddm.conf")
    loaded = []
    history = {}
    for path in sources:
        conf = r.ini(path)
        if conf is None:
            continue
        loaded.append(path)
        for section, keys in {
            "General": ("DisplayServer",),
            "Theme": ("Current",),
            "Wayland": ("SessionDir", "SessionCommand", "CompositorCommand"),
            "X11": ("SessionDir", "SessionCommand"),
            "Autologin": ("Session", "Relogin"),
            "Users": ("RememberLastSession", "DefaultPath"),
        }.items():
            for key in keys:
                if conf.has_option(section, key):
                    history.setdefault(f"{section}.{key}", []).append({"value": conf.get(section, key), "source": path})
                    settings[f"{section}.{key}"] = {"value": conf.get(section, key), "source": path}
    search_path = settings.get("Users.DefaultPath", {}).get("value", "/usr/local/bin:/usr/bin:/bin")
    sessions = []
    for kind, section, folder in (("wayland", "Wayland", "wayland-sessions"), ("x11", "X11", "xsessions")):
        directories = settings.get(f"{section}.SessionDir", {}).get(
            "value", f"/usr/local/share/{folder},/usr/share/{folder}")
        for directory in dict.fromkeys(d.strip() for d in directories.split(",")):
            if not directory.startswith("/"):
                r.warnings.append(f"Unsupported non-absolute session directory: {directory}")
                continue
            for path in r.glob(directory, "*.desktop"):
                entry = r.ini(path)
                if entry is None or not entry.has_section("Desktop Entry"):
                    r.warnings.append(f"Unreadable session entry: {path}")
                    continue
                values = entry["Desktop Entry"]
                name = values.get("Name", Path(path).stem)
                command = values.get("Exec", "")
                try_exec = values.get("TryExec", "")
                try:
                    first = shlex.split(command)[0] if command else ""
                except (ValueError, IndexError):
                    first = ""
                issues = []
                for flag in ("Hidden", "NoDisplay"):
                    if values.get(flag, "false").lower() == "true":
                        issues.append(flag)
                if values.get("Type", "Application") != "Application":
                    issues.append("unexpected Type")
                if not first or not r.executable(first, search_path):
                    issues.append("Exec launcher missing or unrecognized")
                if try_exec and not r.executable(try_exec, search_path):
                    issues.append("TryExec unavailable")
                haystack = (Path(path).stem + " " + name + " " + values.get("DesktopNames", "")).lower()
                desktop = next((key for key, (_, aliases) in DESKTOPS.items()
                                if any(alias in haystack for alias in aliases)), "other")
                if "budgie" in haystack:
                    desktop = "budgie"
                sessions.append({"id": Path(path).name, "name": name, "desktop": desktop,
                                 "kind": kind, "path": path, "exec": command,
                                 "try_exec": try_exec, "issues": issues,
                                 "status": "needs inspection" if issues else "entry detected; login unverified"})
    try:
        dm = r.path("/etc/systemd/system/display-manager.service")
        display_manager = os.readlink(dm) if dm.is_symlink() else "unknown (no symlink)"
    except (OSError, ValueError):
        display_manager = "unknown"
    findings = []
    for key, entries in history.items():
        if len({item["value"] for item in entries}) > 1:
            findings.append({"code": "overridden-setting", "detail": f"{key} has differing values; later files win. This may be intentional.", "evidence": entries})
    remembered = settings.get("Users.RememberLastSession", {}).get("value", "unknown (installed default)")
    findings.append({"code": "remembered-session", "detail": "RememberLastSession=" + remembered + ". Remembering a desktop is not itself a fault; inspect chooser and autologin if it feels stuck.", "evidence": settings.get("Users.RememberLastSession", {})})
    target = settings.get("Autologin.Session", {}).get("value", "")
    if target and target not in {s["id"] for s in sessions}:
        findings.append({"code": "unmatched-autologin", "detail": "Autologin session does not exactly match a detected filename; check installed SDDM semantics.", "evidence": target})
    greeter = settings.get("Wayland.CompositorCommand", {}).get("value", "")
    if "hyprland" in greeter.lower():
        findings.append({"code": "hyprland-greeter", "detail": "The greeter command references Hyprland. Preserve its dependencies even when using another desktop.", "evidence": greeter})
    if "sddm.service" not in display_manager:
        findings.append({"code": "sddm-not-confirmed", "detail": "SDDM is not confirmed by the display-manager link. Do not install or replace the login manager automatically.", "evidence": display_manager})
    version = r.read("/usr/share/omarchy/version")
    return {"schema_version": 1, "omarchy_version": version.strip() if version else "unknown",
            "current_desktop": env.get("XDG_CURRENT_DESKTOP", "unknown"),
            "session_type": env.get("XDG_SESSION_TYPE", "unknown"),
            "display_manager_link": display_manager,
            "uwsm_executable_present": r.executable("uwsm", search_path),
            "sddm_findings": findings, "sddm_config_files": loaded, "sddm_settings": settings,
            "sessions": sessions, "warnings": r.warnings,
            "limitations": ["File evidence only; no successful login or running service verification.",
                            "SDDM paths and parsing are best-effort; verify installed version and defaults.",
                            "No user configuration, service state, packages or logs collected."]}
