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

## Fragment hashing on systemd 261 (2026-09-25)

`fragment-261/` contains a full `--hash-fragment` capture, the exact 386-byte
VM service unit, and two machine-produced comparison reports. The unchanged
tools at `f8aec0d` ran in a fresh, networkless disposable overlay backed by the
preserved revision-5 image. No service or shell settings were changed.

The capture returned 0, saved mode-0600 evidence, and reported SHA-256
`e7ed27417635e1347352cfe571a947e707f59e0cdb28dcaf8519e765a90a8703`.
Independent before/after hashes of the service and shell.json were unchanged.
The service was enabled, active/running; migration readiness stayed false.

Unlike earlier synthetic comparison snapshots, the actual service includes
Unit, Install, environment and restart directives beyond the recognized minimal
fixture. The first guest assertion expecting an accepted comparison failed.
Inspection established the scope mismatch; acceptance was corrected to require
hash agreement while retaining the unsupported-shape refusal. Production tools
and accepted shapes were not changed.

- `match.json`: exact copied unit, `fragment_bytes_match=true`, but exit 1 and
  `recognized_shape=false` / `consistent_observations=false`.
- `different-bytes.json`: only `# Comparison-only comment\n` was prepended to
  the disposable copy. Exit 1, `fragment_bytes_match=false`, and an additional
  provenance mismatch reason. The original unsupported unit shape remains
  unsupported; this is not a successful recognized-shape guest comparison.

Sanitization replaces `/home/omarchytest` with `/home/test`, the observed PID
with 1234 and its start time with midnight on the same date. Only the capture
has the `sanitized=true` envelope field; comparison reports retain their normal
schema. Service bytes, hashes, sizes, state and diagnostic reasons are unchanged.
The snapshot activation link was constructed for this bounded comparison, not
collected as an exhaustive inventory of guest activation sources.

The original consistency tests replayed both reports with their shape refusals.
After the exact-shape review, current tests replay the same inputs with no PATH
tools and compare against these historical reports with only recognition and
its dependent fields updated: matching bytes now pass observation consistency;
changed bytes still fail. Historical JSON is never rewritten. Inputs stay unchanged
and migration readiness remains false. Metadata tests replay the captured manager properties with mocked
queries. The known duplicate bar was still visible; neither this evidence nor
the capture's active state certifies exclusive shell ownership or Plasma health.

The guest unmounted the test disk and shut down normally. Offline QCOW2 and
read-only data-filesystem checks passed. Private raw capture, first-attempt
failure, runner and disk evidence remain under ignored
`evidence/fragment-capture-20260925/`.
