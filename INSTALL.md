# Installation and recovery

Frankenstein v1 supports Omarchy 4.0.4, SDDM 0.21, KDE Plasma Wayland, and the
existing Omarchy/Hyprland session. Other detected SDDM sessions appear in
diagnostics and the theme selector, but are not automatically declared working.

## Package and inspect

Install matching package revisions:

```bash
sudo pacman -U ./frankenstein-core-<version>-x86_64.pkg.tar.zst \
  ./frankenstein-kde-<version>-x86_64.pkg.tar.zst
```

Package installation is inert. It does not change SDDM, user configuration, or
service state. Inspect first:

```bash
frankenstein inspect
frankenstein doctor --json
frankenstein preflight --login frankenstein
```

Source-checkout preflight is `./install.sh --preflight --login frankenstein`.
Preflight checks the exact supported Omarchy version, session desktop files,
shell ownership, SDDM layers and precedence, package payload, and conflicting
paths. It does not request privilege.

## Approved setup

```bash
frankenstein install --login frankenstein
```

Setup prints its complete plan and requires the exact word `INSTALL`. `--yes`
is explicit non-interactive approval intended for controlled tests. Independent
options are:

| Option | Effect |
| --- | --- |
| `--shell auto` | Preserve a detected shell; otherwise install the filtered menu adapter |
| `--shell preserve` | Require and preserve the existing shell |
| `--shell filtered` | Explicitly replace its activation with the filtered adapter while retaining configuration and backup |
| `--login preserve` | Leave theme and autologin untouched |
| `--login chooser` | Install a reversible Breeze/no-autologin override |
| `--login frankenstein` | Install a reversible Frankenstein-theme/no-autologin override |
| `--default keep` | Leave remembered session state untouched |
| `--default auto`, `omarchy`, or `plasma` | Set a supported initial desktop preference |

The installer refuses higher-precedence SDDM settings that would defeat its
proposed fragment. It never rewrites those administrator-owned files to force a
result.

Before mutation it creates:

- `~/.local/state/frankenstein/backups/<UTC timestamp>/`
- `/var/lib/frankenstein/backups/<UTC timestamp>/`

The backups include relevant SDDM files and state, both session entries, the
complete Omarchy configuration tree, and selected KDE configuration. Setup does
not modify KDE panels, wallpaper, shortcuts, KWin, lock-screen, or input
settings.

Setup never restarts SDDM, logs out, or reboots. Save work, then log out
normally and choose a desktop using the prominent session selector.

## Backgrounds

Run this only from a logged-in desktop:

```bash
frankenstein background
```

The command opens `kdialog` or `zenity`, validates a local PNG, JPEG, or WebP
regular file, and requests narrowly scoped Polkit approval to copy it into
`/var/lib/frankenstein/backgrounds/`. It does not grant the greeter general
access to the source directory. The greeter's gear lists the bundled fallback
and validated staged images only.

Selection is persistent. A missing, unreadable, or undecodable selected image
falls back to the bundled vaporwave file. Operational evidence is recorded in
the documented user state file; it contains no password, token, cookie, or
authentication material.

## Verification

```bash
frankenstein verify
frankenstein-shell-adapter check
```

`verify` requires a valid theme payload and at least one verified session and
fails on warnings. `doctor` is less strict and distinguishes detected,
configured, verified, and actually-working evidence. A session is never called
working solely because a desktop file exists.

## Recovery

Restore the active installation record before removing packages:

```bash
frankenstein recover
```

Recovery prints its plan and requires `UNINSTALL`. It removes only
Frankenstein-created integration, restores prior SDDM state, and leaves desktop
packages, user KDE configuration, a preserved Omarchy shell, and all backups
intact. Package dependencies are listed in the backup and are never removed
speculatively.

If synchronization cannot be stopped or SDDM state cannot be restored, recovery
stops with the installation record and backups retained. Resolve the explicit
error and retry; do not delete `state.conf` indiscriminately. `--force` only
bypasses modified Frankenstein-file checks after manual review.

Display-manager restart, logout, and reboot are always separate user actions
after work has been saved.
