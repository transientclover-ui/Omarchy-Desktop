# Login watchdog and flight recorder

The core package supplies a one-shot user service pulled in by
`graphical-session.target`. It checks only recorded installations belonging to
the current user. Plasma Wayland delegates health to the existing shell adapter;
unsupported desktops exit silently until they have an adapter. Healthy sessions
create no incident and leave no watchdog process. Intentionally disabled shell
integrations are skipped. No timer or continuous polling is installed.

Three bounded checks allow startup to settle. A runtime marker and lock permit
one invocation per login, including failures and manual service re-entry. The
marker is written before checks; if interrupted, the watchdog does not retry.
On failure, service scalar states and recent per-unit journal excerpts are saved
and synced to disk before recovery is considered. The evidence is retained even
if recovery succeeds. Failure to save evidence prevents recovery.

There is at most one shell restart, followed by one health check. Filtered mode
requires the Frankenstein shell service to match its packaged template. Preserve
mode includes the recorded, enabled Omarchy shell with the exact stock Quickshell
launcher, no drop-ins and no auxiliary Exec commands. Custom services are
recorded but not restarted. Desktop-owned services are diagnostics only: KWin,
Plasma, Hyprland and GNOME Shell are never restarted. Existing service restart
policies are not changed by this feature. A watchdog incident is evidence of a
bug to diagnose and fix, even when the restart restores health.

Commands:

```
frankenstein watchdog incidents
frankenstein watchdog tail
```

Incidents are under `${XDG_STATE_HOME:-$HOME/.local/state}/frankenstein/watchdog/incidents`.
Directories use mode 0700 and files 0600. Retention is ten incidents, thirty days,
64 KiB per incident and 640 KiB total, enforced during capture and CLI access.
Only selected identity fields, fixed service properties and two-minute journal
tails (30 entries, 2 KiB per command) are collected. No environment dump,
configuration dump, process command lines or uploads are used. Sensitive lines,
URLs, home paths and long opaque values are filtered. Filtering is heuristic;
review incidents before sharing, because applications may log sensitive text in
unrecognized formats. Commands time out after eight seconds; service execution
has a 180-second outer bound. A stalled restart may finish asynchronously in
systemd; no second restart is issued.

Package upgrades replace the executable and unit. Removing the core package
removes the target dependency and unit; the current invocation should be stopped
before removal. Integration uninstall invalidates the installation record and
future checks skip it. Incidents remain for diagnosis and may be deleted manually.
Rollback to the previous package removes this package's watchdog files; existing
incident evidence is preserved. No user config reset is required.
