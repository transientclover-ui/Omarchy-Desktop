# Installer

Frankenstein currently supports **Omarchy 4.0.4 with KDE Plasma Wayland**.
GNOME and other desktops are intentionally out of scope.

## Preflight

### Pacman packages

Install both packages from the same build:

```bash
sudo pacman -U ./frankenstein-core-<version>-x86_64.pkg.tar.zst \
  ./frankenstein-kde-<version>-x86_64.pkg.tar.zst
```

Package installation only installs files under `/usr`; it does not alter user
configuration, enable services, or change SDDM. Run the read-only assessment
explicitly:

```bash
frankenstein preflight
```

Then configure the KDE adapter:

```bash
frankenstein setup
```

For development directly from a source checkout, run:

```bash
./install.sh --preflight
```

The preflight validates the operating system, exact supported Omarchy version,
original Omarchy session, installed shell source layout, Plasma session, SDDM
state, and any existing user shell service. It prints the complete change plan
and exits without requesting privilege.

If Plasma's packaged Wayland session is already valid, the installer adopts it
and performs no package transaction. If Plasma is absent, the approved install
uses:

```bash
omarchy pkg add plasma-meta
```

## Installation

```bash
./install.sh
```

The installer requires the user to type `INSTALL` after reviewing the plan.
`--yes` is intended for controlled automated testing and constitutes explicit
consent.

Backups are created before package or configuration changes:

- `~/.local/state/frankenstein/backups/<UTC timestamp>/`
- `/var/lib/frankenstein/backups/<UTC timestamp>/`

The complete Omarchy user configuration and relevant KDE configuration files
are archived. KDE panel, wallpaper, theme, shortcut, KWin, lock-screen, and
input files are not edited.

The installer does not restart SDDM. Log out normally after installation and
choose Plasma from the session selector.

## Verification

Inside Plasma:

```bash
frankenstein-shell-adapter check
```

A passing result requires exactly one filtered shell instance, working IPC,
and `omarchy.menu` as the only enabled Omarchy Shell plugin. Plasma remains the
native owner of its panel, launcher, wallpaper, lock/idle behavior,
notifications, Polkit agent, workspaces, and OSD.

## Rollback

For a package installation:

```bash
frankenstein uninstall
```

After successful configuration rollback, the packages can be removed
separately with pacman. Removing packages first also removes the packaged
rollback command, so it is not the recommended order.

For a standalone source installation:

```bash
./uninstall.sh
```

Rollback removes only Frankenstein-created files, restores the prior
`omarchy-shell.service` enablement state, and leaves KDE configuration and
packages intact. Use `--force` only after manually reviewing locally modified
Frankenstein files.

Packages added during installation are listed in the timestamped backup but
are not automatically removed. Removing a desktop dependency closure after it
has been used or customized is unsafe; package rollback remains an explicit
administrator decision.

If setup fails after changes begin, it removes the SDDM override, user
autostart/application files, default-session service state, and any
standalone-installed payload. It also restores the prior
`omarchy-shell.service` enablement and active state. Packages installed as
dependencies are intentionally retained and listed in the timestamped backup.

## Current fresh-overlay status

The first package and setup run on an untouched Omarchy 4.0.4 baseline is
recorded in `COMPATIBILITY-JOURNAL.md`. Package installation, setup, rollback
after an injected setup failure, Breeze session selection, Plasma and Omarchy
sessions, package upgrade and downgrade, configuration rollback, and package
removal passed. The initial Plasma black screen was fixed in package revision
2 by adding the required `plasma-desktop` dependency. See the journal for the
complete evidence and remaining limitations.
