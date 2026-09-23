# Installer

Frankenstein currently supports **Omarchy 4.0.4 with KDE Plasma Wayland**.
GNOME and other desktops are intentionally out of scope.

The current source includes an **existing-shell preservation path**. When an
`omarchy-shell.service` already exists, setup keeps its configuration and
active/enabled state and does not start a second, filtered shell. This path has
isolated regression coverage but still needs packaged graphical-VM validation.
It does not certify every existing plugin's behavior under KDE.

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

Then add integration while preserving existing settings by default:

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
and exits without requesting privilege. Existing Frankenstein integration files
(including dangling symlinks) are refused before mutation. Standalone setup also
refuses existing helper payloads. Review conflicts instead of deleting them
blindly.

SDDM settings are read in vendor-fragment, local-fragment, then main-file order.
If a higher-precedence setting would defeat the proposed Breeze/no-autologin
fragment, setup stops for review rather than editing that existing configuration.

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

The default setup preserves the existing shell when present, SDDM theme,
autologin configuration and remembered desktop. Without an existing shell
service, it adds the filtered menu-only adapter. Existing KDE appearance,
shortcuts, panel, wallpaper and other configuration are not replaced.

Choose categories independently when you want changes:

| Option | Effect |
| --- | --- |
| `--shell auto` (default) | Preserve an existing shell service; otherwise add the filtered adapter |
| `--shell preserve` | Require and preserve the existing shell service |
| `--shell filtered` | Explicitly replace the existing service with the menu-only adapter; its configuration stays backed up and intact |
| `--login preserve` (default) | Keep the current SDDM theme and autologin settings |
| `--login chooser` | Request a reversible Breeze/no-autologin override |
| `--default keep` (default) | Leave remembered session state unchanged |
| `--default auto`, `omarchy` or `plasma` | Explicitly set a supported initial desktop preference |

For example, `frankenstein preflight --login chooser` previews a login chooser
without replacing an existing Omarchy shell. Repeat the same options with
`frankenstein setup` only after reviewing that plan. Existing autologin can
still override desktop selection when login settings are preserved.

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

## Individual plugins and custom widgets

`frankenstein settings` opens an opt-in selection for the running stock Omarchy
shell. All currently enabled, selectable plugins and each configured bar widget
start selected. Keep everything to leave `shell.json` byte-for-byte unchanged.
Custom command widgets are included even though they have no plugin manifest;
keeping one preserves its commands, click action, interval, position and other
fields. Duplicate widget instances can be selected separately.

Unchecking a plugin disables it and removes its linked bar widgets. Unchecking
one widget removes that occurrence without resetting unrelated configuration.
Already-disabled plugins stay disabled, the bar itself is retained, and no
plugin is installed or newly enabled. Custom scripts are not executed or edited.
The tool shows a diff, requires `APPLY`, saves the original configuration under
`~/.local/state/frankenstein/settings-backups/`, and refuses a detected concurrent
edit. Applying choices changes the live shell configuration and can hot-reload
it; setup never runs this selector automatically.

For inspection only, use `frankenstein settings --list`. A JSON array of catalog
keys can be passed to `frankenstein settings --preview KEEP_JSON` to preview
choices without writing settings. Source installations use
`frankenstein-settings` directly. The selector requires a regular user-owned
`shell.json` with an explicit bar layout and a responding stock shell; it
refuses unsupported layouts rather than inventing defaults.

Use `frankenstein desktop` (or `omarchy-default-desktop --choose-and-switch` in
a standalone installation) to choose a default and optionally confirm logout.
This remains available when the existing shell is preserved; its menu extension
is not overwritten to add the command.

## Verification

Inside Plasma:

```bash
frankenstein-shell-adapter check
```

For a preserved shell, the check reports its service/IPC availability and
explicitly states that plugin compatibility is not certified. `enable`,
`disable` and `run` refuse to replace or control that user-owned shell.

For the filtered profile, a passing result requires exactly one filtered shell instance, working IPC,
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

Rollback removes Frankenstein-created integration and leaves KDE configuration
and packages intact. Preserved shells are not stopped, enabled or restarted.
An explicitly replaced shell has its prior service state restored. Settings
changed separately through the opt-in selector are user choices; uninstall does
not reset them. Their original files remain in the selector backup directory. Use `--force` only after manually reviewing locally modified
Frankenstein files.

Packages added during installation are listed in the timestamped backup but
are not automatically removed. Removing a desktop dependency closure after it
has been used or customized is unsafe; package rollback remains an explicit
administrator decision.

When automatic rollback succeeds after a setup failure, it removes the SDDM override, user
autostart/application files, default-session service state, and any
standalone-installed payload. It also restores the prior
`omarchy-shell.service` enablement and active state. Packages installed as
dependencies are intentionally retained and listed in the timestamped backup.

If stopping SDDM synchronization or restoring its prior state fails, cleanup
stops and reports incomplete recovery. Keep the retained backups and payload;
resolve the reported error before retrying uninstall for an active installation.
A failed setup may require manual recovery from its reported backup directory.

## Current fresh-overlay status

The first package and setup run on an untouched Omarchy 4.0.4 baseline is
recorded in `COMPATIBILITY-JOURNAL.md`. Package installation, setup, rollback
after an injected setup failure, Breeze session selection, Plasma and Omarchy
sessions, package upgrade and downgrade, configuration rollback, and package
removal passed. The initial Plasma black screen was fixed in package revision
2 by adding the required `plasma-desktop` dependency. See the journal for the
complete evidence and remaining limitations.

The later KDE adoption and rollback changes in the current source tree have only
local isolated tests so far, including packaged and standalone control flow,
KDE configuration backup/preservation, and SDDM precedence/conflict checks.
They have not yet been rebuilt and validated in a fresh graphical VM. The
previous VM results do not certify these newer changes or non-menu profiles.
