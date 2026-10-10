# Wallpaper ownership with the preserved stock shell

On KDE Plasma Wayland, the stock Omarchy shell can render its own background
surface over Plasma's wallpaper without changing Plasma's saved image.
The filtered Frankenstein adapter already excludes that renderer by default.
For installations deliberately preserving the stock shell, run as the desktop user:

```sh
frankenstein-plasma-wallpaper install
```

This opt-in repair leaves the stock shell service, bar, menu and other plugins
in place. It backs up `~/.config/omarchy/shell.json` under
`~/.local/state/frankenstein/plasma-wallpaper/`, adds only `omarchy.background`
to `disabledPlugins`, and asks the running shell to unload that service. A
failed live IPC call exits unsuccessfully; the saved fix remains available.
It does not modify Plasma's wallpaper configuration or the Omarchy background link.

The command installs a user service drop-in for `omarchy-shell.service`.
Before each service start, it disables the renderer only when the service's
session environment contains KDE and `XDG_SESSION_TYPE=wayland`.
After the shell stops, or before a start outside Plasma Wayland, it removes
only the disable entry it owns. Existing user disables remain disabled.
Changes to other settings made while the repair is active survive restoration.
This avoids carrying the repair's background disable into Hyprland sessions.
The systemd user manager must have the correct session environment, as required
by the stock shell's own Wayland startup condition. A shell started outside
this service bypasses the start/stop hooks.

To remove the repair:

```sh
frankenstein-plasma-wallpaper remove
```

Restart the shell to load a restored preference. Backups are retained.
This is separate from shell adoption and is not imposed by `--shell preserve`.
When running from source, keep the executable at a stable path: the drop-in
records its absolute path. Packaged installations use `/usr/bin`.

Validate with `python3 tests/plasma-wallpaper.py`. On a live host, verify
`omarchy-shell shell listPlugins` reports the background disabled and the bar
active, and that Plasma's live desktop objects still reference its selected
wallpaper. A successful check removes the known competing renderer; it does
not prove the cause of every historical switch or exclude future independent
wallpaper changes.
