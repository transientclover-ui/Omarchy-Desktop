# Desktop-aware shell restart

`frankenstein shell restart` uses the existing user shell service on KDE Plasma
Wayland, rather than attempting a Hyprland dispatch. It restarts either the preserved
`omarchy-shell.service` or the active `frankenstein-omarchy-shell.service` adapter,
and waits up to 20 seconds for both active service state and successful shell IPC.
If both services are active, or two inactive units leave ownership ambiguous, it
refuses instead of creating another shell. A single loaded inactive unit can be
restarted after a failure. The shell's existing service drop-ins still run.

Outside KDE Wayland it delegates to `/usr/bin/omarchy-restart-shell`, preserving
upstream Hyprland lock/relock checks and its canonical launch path. It does not
enable services or change desktop/session configuration. Desktop selection uses
`XDG_CURRENT_DESKTOP` and `XDG_SESSION_TYPE` inherited from the active session.

## Route existing Omarchy commands too

Run `frankenstein-shell-restart install` as the desktop user. This installs:

- `~/.local/bin/frankenstein-shell-restart`: the helper.
- `~/.local/bin/omarchy`: intercepts only the exact `restart shell` command;
  other commands and help go to `/usr/bin/omarchy`.
- `~/.local/bin/omarchy-restart-shell`: routes direct no-argument restart calls.
- `~/.config/environment.d/60-frankenstein-shell-restart.conf`: places the user
  command directory before system commands on the next login.

It refuses to overwrite unrelated user commands. Previous owned files are backed
up under `~/.local/state/frankenstein/shell-restart/backups/`. Removing the owned
files with `frankenstein-shell-restart remove` returns command routing to stock.
No package-owned Omarchy files are edited. The environment PATH preference affects
all user commands on subsequent sessions; only the two installed Omarchy wrappers
are changed by this fix. Existing terminals retain their old PATH until they are
updated or a new session is started. To use immediately in such a terminal:

```sh
export PATH="$HOME/.local/bin:$PATH"
omarchy restart shell
```

The local installation also updated the current user-manager PATH and restarted
the existing Omarchy service, so its menu actions use the new routing now. No
service enablement or inference startup was performed.

## Validation

`python3 tests/shell-restart.py` passes selection, duplicate-ownership rejection,
stock Hyprland delegation, KDE service restart, startup IPC retry, wrapper
install/update/remove, and unrelated-command preservation tests. The package
manifest includes the helper and its source checksum.

On the available KDE Plasma Wayland session, `omarchy restart shell` through the
wrapper restarted the preserved service and returned `shell IPC ready`. The live
RP AI widget returned `Offline`, background remained disabled, and the shell
reported `active`, `NRestarts=0`. Other Omarchy commands still delegate to stock;
`omarchy version` returned 4.0.4-1. No live Hyprland, filtered-adapter, logout,
reboot, or rebuilt Arch-package installation was tested. Unit tests cover the
Hyprland delegation behavior; this is not a live Hyprland validation claim.
