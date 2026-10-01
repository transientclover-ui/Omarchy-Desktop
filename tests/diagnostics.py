#!/usr/bin/env python3
"""Fixture tests for the read-only Frankenstein diagnostic model."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "src/libexec/frankenstein-diagnostics"


def put(root: Path, name: str, content: str, mode: int = 0o644) -> Path:
    path = root / name.lstrip("/")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(mode)
    return path


class DiagnosticsTests(unittest.TestCase):
    def run_tool(self, root: Path, command: str = "inspect"):
        env = dict(os.environ, FRANKENSTEIN_ALLOW_FIXTURE_ROOT="1")
        result = subprocess.run(
            [str(TOOL), command, "--json", "--root", str(root)],
            text=True,
            capture_output=True,
            env=env,
            timeout=5,
        )
        return result, json.loads(result.stdout)

    def fixture(self, root: Path):
        put(
            root,
            "/usr/share/wayland-sessions/plasma.desktop",
            "[Desktop Entry]\nType=Application\nName=Plasma\nExec=/usr/bin/startplasma-wayland\n",
        )
        put(
            root,
            "/usr/share/wayland-sessions/omarchy.desktop",
            "[Desktop Entry]\nType=Application\nName=Omarchy\nExec=/usr/bin/uwsm start hyprland.desktop\n",
        )
        put(
            root,
            "/etc/sddm.conf.d/10-base.conf",
            "[Users]\nRememberLastSession=true\n[Theme]\nCurrent=breeze\n",
        )

    def test_mixed_sessions_layering_and_remembered_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            put(
                root,
                "/etc/sddm.conf.d/zzzz-frankenstein.conf",
                "[Theme]\nCurrent=frankenstein\n[Autologin]\nUser=\nSession=\n",
            )
            put(root, "/usr/share/sddm/themes/frankenstein/Main.qml", "Item {}\n")
            put(root, "/usr/share/sddm/themes/frankenstein/metadata.desktop", "[SddmGreeterTheme]\n")
            state = {
                "schema_version": 1,
                "frankenstein_version": "0.1.0",
                "theme_version": "1",
                "theme_installed": True,
                "theme_active": True,
                "selected_background": "/usr/share/sddm/themes/frankenstein/background.png",
                "default_background": "/usr/share/sddm/themes/frankenstein/background.png",
                "last_known_valid_background": "/usr/share/sddm/themes/frankenstein/background.png",
                "sddm_configuration_path": "/etc/sddm.conf.d/zzzz-frankenstein.conf",
                "previous_theme": "breeze",
                "backup_location": "/var/lib/frankenstein/backups/example",
                "detected_sessions": ["omarchy.desktop", "plasma.desktop"],
                "last_validation": {"version": "0.1.0", "timestamp": "2026-01-01T00:00:00Z"},
            }
            put(
                root,
                "/home/test/.local/state/frankenstein/sddm-state.json",
                json.dumps(state),
            )
            result, report = self.run_tool(root, "verify")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(report["sddm"]["theme"], "frankenstein")
            self.assertTrue(report["sddm"]["remember_last_session"])
            self.assertEqual([item["id"] for item in report["sessions"]],
                             ["omarchy.desktop", "plasma.desktop"])
            self.assertTrue(all(item["verified"] for item in report["sessions"]))
            self.assertTrue(report["state"]["valid"])

    def test_malformed_hidden_missing_and_autologin(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            put(root, "/etc/sddm.conf.d/bad.conf", "[Theme\nCurrent=broken\n")
            put(
                root,
                "/etc/sddm.conf.d/login.conf",
                "[Autologin]\nUser=test\nSession=missing.desktop\n",
            )
            put(
                root,
                "/usr/share/wayland-sessions/hidden.desktop",
                "[Desktop Entry]\nName=Hidden\nHidden=true\n",
            )
            put(
                root,
                "/usr/share/wayland-sessions/try.desktop",
                "[Desktop Entry]\nName=Try\nExec=/usr/bin/true\nTryExec=/missing\n",
            )
            put(
                root,
                "/home/test/.local/state/frankenstein/sddm-state.json",
                '{"schema_version": 99}',
            )
            result, report = self.run_tool(root, "doctor")
            self.assertEqual(result.returncode, 1)
            codes = {item["code"] for item in report["findings"]}
            self.assertTrue(
                {
                    "malformed-sddm-config",
                    "autologin-bypasses-chooser",
                    "invalid-session",
                    "state-invalid",
                }.issubset(codes)
            )

    def test_inspect_is_read_only_and_json_is_stable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.fixture(root)
            before = {
                str(path.relative_to(root)): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            first, report = self.run_tool(root)
            second, _ = self.run_tool(root)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout, second.stdout)
            self.assertTrue(report["read_only"])
            self.assertEqual(
                before,
                {
                    str(path.relative_to(root)): path.read_bytes()
                    for path in root.rglob("*")
                    if path.is_file()
                },
            )


if __name__ == "__main__":
    unittest.main()
