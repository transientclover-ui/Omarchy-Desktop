# Real-manager observation

`systemd-261-active.json` was transcribed from the two exact `systemctl --user
--no-pager show --all` queries used by the collector, run in the disposable VM
on 2026-09-23. The guest reported systemd 261 (261.2-1-arch), with its existing
Omarchy shell service enabled and active under Hyprland. The user-manager
UnitPath order and all requested properties were visible in the guest console.

Sanitization replaces the account home with `/home/test`, the process ID with
1234, and its start time with midnight on the observation date. UID 1000 is the
VM test UID. No credential is included. ExecStart is opaque observation text,
not a command to execute. This is a normalized transcription, not a byte-for-byte
capture file. The replay test validates parsing of these observed values.

This does not certify exclusive shell ownership, the inactive case, Plasma
behavior, or a full capture-runner execution in the guest. The guest visibly
reproduced the already documented duplicate-bar limitation; no fix was attempted.

## Full capture-runner observations (2026-09-24)

The three `systemd-261-capture-*.json` fixtures were produced by the full capture
runner and collector at `ec1cc6d` inside a fresh disposable overlay backed by
the preserved revision-5 VM. Scripts arrived on an automounted removable test
disk, not through console transcription. The VM had no network device.

- `active`: existing enabled service, active/running.
- `inactive`: same service after an explicit guest-only stop, still enabled,
  inactive/dead; ExecStart records termination by SIGTERM.
- `restart-attempt`: after an explicit guest-only start, still enabled but
  inactive/dead, with ExecStart recording exit status 0. This is not evidence
  of successful active-state restoration or a diagnosis of the exit cause.

All three runner results had exit status 0, complete metadata and no review
reasons. This means the metadata format/state was accepted, not that a shell
was healthy: `migration_ready` remains false. User-manager metadata collection
is deliberately separate from the preserved-shell health check.

The saved reports had mode 0600. SHA-256 checks confirmed unchanged guest
`shell.json` and service-unit bytes. The guest was shut down normally after
unmounting the data disk. Offline QCOW2 and read-only data-filesystem checks
passed. Raw private evidence stays in the ignored evidence directory.

Sanitization changes only `/home/omarchytest` to `/home/test`, PIDs to 1234/1235,
and observed times to 00:00/00:01/00:02 on the original date. `sanitized` is set
to true after these changes. Other reported values and search-path order are
preserved. The earlier transcribed fixture remains separate historical evidence.
These tests do not certify Plasma behavior, exclusive shell ownership or the
resolution of the already documented cross-session launcher conflict.
