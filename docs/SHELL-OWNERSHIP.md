# Shell ownership across KDE and Omarchy

Status: proposed implementation contract, not an available setup mode or a
validated release. This document addresses the duplicate-launcher failure in
the revision 5 disposable VM. It does not authorize host adoption.

## Current behavior and evidence

`install.sh` defaults to `--shell auto`: preserve an existing
`omarchy-shell.service`, otherwise install the filtered menu-only adapter.
`--shell preserve` requires an existing service. Preservation leaves its unit,
active/enabled state and shell configuration unchanged; adapter run/enable/disable
refuse to control it. Explicit `--shell filtered` replaces that service with the
filtered adapter and records its prior state for restoration.

The revision 5 VM fixture's preserved service competed with Omarchy's native
launcher on Hyprland login. One trial left the service inactive with working
IPC; another started two stock-shell instances. The current health check detects
these conditions but does not resolve ownership. A passing preserved-shell
check requires an active service, working IPC and exactly one valid instance
for the stock configuration on the current display. This is not a Hyprland
ownership check or a certification of individual plugins.

## Policy decision

Keep auto/preserve behavior unchanged. Merely discovering an existing service
must never opt the user into lifecycle changes. Introduce any future managed
ownership choice separately, with an explicit preview and selection; its CLI
spelling remains to be decided. It must not be implied by `--yes`, a desktop
selection, a health failure or an upgrade of an existing preservation install.

For that opt-in choice, ownership is:

| Session | Sole launch owner | Required behavior |
| --- | --- | --- |
| Plasma Wayland | A Frankenstein-owned Plasma-scoped service launching the preserved stock configuration | Start once after Plasma is ready; stop and wait for exit at native logout |
| Omarchy/Hyprland | Omarchy's existing native launcher | No Frankenstein stock-shell service or autostart remains active |
| No graphical session | None of the managed Plasma integration | No shell survives through this integration |
| Unknown desktop or overlapping graphical sessions for the same user | No new managed launch | Refuse activation, report ambiguity and leave unrelated processes alone |

The managed Plasma service must reuse the reviewed existing launch command and
required environment without rewriting the original unit or reducing its
configuration. Support initially only a narrowly recognized unit shape. Refuse
unknown wrappers, other activation paths, masks, aliases, unsupported overrides,
or dependencies whose behavior cannot be preserved. Do not copy arbitrary unit
text and assume equivalent behavior. The supported shape and real session
identity mechanism must be established by the subsequent read-only inventory.

Session identity must not rely solely on potentially stale environment variables
in a persistent user manager. Plasma target membership and startup ordering
alone are not proof that another graphical session has ended. Before launching,
verify the supported current session and absence of another stock-shell instance
on its display; ambiguity or a failed query blocks launch. Do not kill an
unowned process to satisfy the check. Instance counting is a guard, not a lock:
all supported competing activation paths must be excluded before claiming that
two launchers cannot race.

## Preserve the customized desktop

Keep `shell.json`, plugin settings, disabled choices, custom scripts and widget
fields byte-identical during setup, session transitions and rollback. Preserve
the user's workspaces/idle/lock/nightlight/monitor disabled choices. Do not enable
components based on an installed manifest or reset the bar layout. Compatible
optional components, including the Omarchy top bar and custom widgets, remain
part of the intended design. Menu-only remains the conservative fresh default.

Lifecycle ownership does not resolve notification, Polkit, lock or other plugin
compatibility. Retain observed native ownership and report conflicts; do not
claim all enabled registry entries work or silently disable them. Per-widget
selection remains a separate explicit operation with its own backup and review.

## Reversible activation and recovery

1. Read-only preflight identifies the effective original unit, drop-ins,
   activation links, launch command, session and process state. Preview the exact
   ownership changes and unsupported findings before accepting opt-in.
2. Before mutation, record original bytes, metadata, symlink targets and exact
   enablement/activation state in durable recovery data. Existing boolean
   enabled/active fields are insufficient for a general unit migration. Refuse
   unsupported states rather than treating them as ordinary disabled units.
3. Recheck the reviewed inputs for concurrent edits. Stage only new,
   Frankenstein-owned files; refuse collisions. Persist each completed mutation
   so interrupted setup can recover without assuming a completed installation.
4. At a documented safe boundary, remove the recognized original activation
   path and stop/wait for its service before permitting the new Plasma owner.
   Preserve the original unit/configuration files. Do not restart SDDM or stop
   the desktop. Never introduce a second owner to avoid a brief shell gap.
5. Verify the selected session, sole instance and IPC. Any failure reports
   incomplete activation and attempts reversal in reverse mutation order.
6. On uninstall or failed setup, stop/wait for the managed owner before removing
   its files or restoring original activation. If stopping or restoring fails,
   retain recovery records and needed payload, report incomplete cleanup and
   allow retry. Never report success or discard the record while ownership is
   uncertain. Refuse to overwrite intervening user edits.

Restoring enablement is distinct from starting a process. Immediately after a
failed setup in the same supported Plasma session, restore the previously
active original service only after confirming the replacement has exited and
no competing stock instance exists. During later uninstall from Hyprland or
another session, restore the original persistent configuration but defer a start
that would compete with the native shell. Explain the deferred restoration.
An originally inactive service must not be started. Restoring an originally
conflicting configuration can restore the original limitation; rollback must
not promise to repair that user-owned configuration.

## Acceptance cases

These are required future tests, not reported passes. Use temporary filesystem
fixtures and simulated services first, then a fresh disposable baseline-backed
VM for real session behavior. Never run these mutation cases on the host.

| Case | Required evidence |
| --- | --- |
| Default auto/preserve with active or inactive existing service | No lifecycle mutations; exact config/widget preservation; no replacement owner |
| Fresh install without existing service | Conservative filtered default retained |
| Opt-in with supported active service | Stop/wait precedes new start; one owner; original bytes retained |
| Opt-in with inactive service | No unsolicited shell start; activation intent shown explicitly |
| Unknown unit, extra autostart, masked/aliased service or concurrent edit | Refusal before mutation with actionable reason |
| Failure after each mutation, including stop, reload, start and health check | Accurate failure status; reverse-order recovery or retained retryable state |
| Interrupted setup and recovery retry | Completed mutations discoverable; no duplicate activation or lost backup |
| Uninstall in Plasma, Hyprland and outside a graphical session | Session-safe restoration; originally inactive stays inactive; no competing start |
| Modified owned file or failed cleanup | No silent overwrite; recovery record/payload retained |
| KDE → Omarchy → KDE, repeated twice | Native logout; exactly one expected shell after each login; outgoing managed owner gone |
| Reboot into each desktop, twice each | Correct launch owner with no intermittent duplicate or restart loop |
| Unknown/stale session environment or overlapping sessions | No new managed launch; explicit unsupported-state report |
| Top bar, representative custom widget and disabled components | Bytewise config preservation plus graphical/functional checks; no plugin-certification claim |

VM evidence must include session identity, service states, instance/PID lists,
IPC, logs, configuration hashes and native desktop/portal ownership. Exercise
both packaged and standalone rollback paths locally. Package checksums, a fresh
revision when required, reproducible builds and validation of those exact
packages remain separate release requirements.

## Offline inventory implemented

Run the development-only assessor on a stable, disposable directory snapshot:

```bash
python3 tools/shell-ownership-inventory.py SNAPSHOT
```

The snapshot must contain real `units/` and `autostart/` directories. It has no
implicit host paths and does not invoke systemctl, execute unit/widget commands,
write files or follow discovered symlinks. Use a private snapshot that is not
being changed concurrently; this is not a race-safe filesystem security boundary.
The tool is not packaged or connected to setup.

The first recognized shape is deliberately the existing preservation-test fixture:

```ini
[Service]
ExecStart=/usr/bin/quickshell -n -p /usr/share/omarchy/shell
```

Only blank lines and full-line comments may vary. The unit must be a regular
`units/omarchy-shell.service` file. Its optional sole activation link is
`units/graphical-session.target.wants/omarchy-shell.service`, targeting exactly
`../omarchy-shell.service`. No link means only “no link in this snapshot,” not
that the real service is disabled. The snapshot's autostart directory must be
empty. Additional files/directories, drop-ins, aliases, masks, wrappers and
alternate activation paths are conservatively reported as unsupported; even an
unrelated unit is unassessed rather than assumed harmless.

JSON output includes file hashes/modes, link targets, activation observations,
reasons for refusal and unassessed areas. Exit 0 means only that the snapshot
matches this narrow shape; exit 1 means unsupported or incomplete inventory.
`migration_ready` is always false. The assessor does not establish effective
systemd precedence, live enablement/active state, sessions, processes, or absence
of launch paths outside those supplied directories. It does not inspect or
change shell configuration, custom widgets or plugin choices.

Validation uses `python3 -W error tests/shell-ownership-inventory.py` with
disposable fixtures, including unchanged input bytes/metadata and commands that
must never execute. These tests do not establish support for an actual live
unit or resolve the cross-session race.

## Read-only manager metadata collector

The separate development tool `python3 tools/shell-ownership-metadata.py`
queries the current user's systemd manager twice using only `systemctl --user
show`: once for the named service and once for the manager's `UnitPath`.
It has a five-second timeout per query. It does not load file contents, run
launch commands, reload the manager or change service state. It is not invoked
by setup, packaged, or automatically combined with the offline snapshot.

JSON retains the reported unit identity/names, load and unit-file states,
fragment/source/drop-in paths, active/substate, reload requirement, raw ExecStart
metadata and raw manager search paths. Simple absolute search paths are also
returned in order as an array; escaped/quoted or ambiguous serialization is
reported for review rather than guessed. Search paths are observations, not
proof that every activation path was inspected. Raw command metadata may contain
private arguments; review before sharing the report.

`metadata_collected` means both requested property sets were returned intact.
Masks, aliases, drop-ins, generated units, stale manager configuration and
unsupported states produce review reasons even when collection succeeds.
Missing/duplicate/malformed properties, query failures and timeouts fail
conservatively. Exit 0 means only collected metadata with no listed findings;
exit 1 means collection failed or review is required. `migration_ready` is
always false. No file shape, plugin compatibility or session ownership is
certified by a successful query, and the two observations are not atomic.

Run `PYTHONDONTWRITEBYTECODE=1 python3 -W error
tests/shell-ownership-metadata.py` for mocked tests that never contact host
systemd. The exact query properties and simple search-path serialization were checked
against systemd 261 in a disposable VM; the sanitized active-service observation
is retained under `tests/fixtures/shell-metadata/`. On 2026-09-24 the full guest
collector/capture path also passed for enabled active and enabled inactive
states. Sanitized captured reports and replay tests are retained there.

## Guest-side evidence capture

A development-only capture runner is ready for the disposable guest:

```bash
python3 tools/capture-shell-ownership-metadata.py /private/guest-directory/metadata.json
```

Use an existing private directory and a new output filename. The runner invokes
only the collector, stores its report and exit status in a mode-0600 JSON file,
and refuses to overwrite an existing file or final symlink. Exit 0/1 preserves
the collector result; exit 2 means capture failed. Capture success does not mean
that the metadata is supported. Reports are explicitly marked unsanitized:
review paths and launch arguments before retaining a public fixture. The runner
does not change a unit to manufacture an enabled, inactive or override scenario.

`tests/shell-ownership-metadata-capture.py` exercises the full runner/collector
command path with a fake systemctl on an isolated PATH. Eight cases cover active
and inactive observations, overrides, query/malformed-output failures and safe
output creation. Those cases use simulated manager responses. Separate real
VM captures cover active, stopped and attempted-restart observations. The last
remained inactive despite an exit-0 start; it is not a restoration success.
See the fixture README for provenance, sanitization and validation limits.

## Optional fragment-byte capture

Add `--hash-fragment` to the capture runner to record the file currently at the
reported FragmentPath. Default capture remains metadata-only. The new optional
`fragment` field records the path, an explicit `ok`/`refused` outcome and, only
on success, SHA-256 and byte count. No unit contents are included in the report.

This Linux-specific reader refuses noncanonical paths, symlinks in any path
component, non-regular files and files larger than 1 MiB. It uses nonblocking
opens, bounds the read, compares descriptor identity/metadata before and after,
and securely reopens the original path to detect replacement. Detected changes
or read failures emit a refusal with no hash. This is a bounded observation;
it cannot prove freshness after the read or the bytes already loaded by systemd.
Concurrent changes that are not observable in these checks remain outside its
claim. Like other file reads, access-time accounting may be updated by the OS.

If metadata collection is incomplete, no fragment is opened. With the flag, the
saved `capture_exit_status` and command exit status are 1 on a refused fragment,
while `collector_exit_status` retains the separate metadata result. Output
creation failures still return 2. Even refused observations are saved as private
evidence. The path/hash may identify private configuration; sanitize before
sharing. The flag does not change a service, unit or shell setting.

`tests/shell-fragment-provenance.py` exercises disposable files and injected
replacement, rewrite and I/O failures. The capture CLI and comparison suites
also cover the optional fields. A systemd-261 disposable-VM capture now validates successful fragment hashing
and comment-only snapshot mismatch detection. The actual VM unit has directives
outside the recognized minimal shape: exact bytes yield a hash match but still
refuse overall consistency. Both full reports and the exact unit are replayed
in tests; see `tests/fixtures/shell-metadata/README.md`. This does not validate
an accepted real-unit shape, Plasma behavior or exclusive ownership.

## Offline capture/snapshot consistency

The existing inventory can optionally compare a saved capture against its
recognized snapshot shape:

```bash
python3 tools/shell-ownership-inventory.py SNAPSHOT \
  --capture CAPTURE.json \
  --source-unit-directory /home/test/.config/systemd/user
```

Both options are required together. The source directory is an explicit mapping
for `SNAPSHOT/units/`, not a path the tool opens. Use the captured original
absolute directory (or the same normalized path when replaying sanitized
fixtures); do not substitute the snapshot's current location.

The comparison reuses the collector's assessment rules on the saved raw
properties without querying systemd. It refuses unsuccessful, malformed or
internally inconsistent captures, duplicate JSON fields and unsupported property
types. It checks that the mapped fragment is exactly `omarchy-shell.service`,
that the mapped directory occurs in the captured search path, and that the
single observed ExecStart serialization matches the snapshot's direct launch
command. Wrappers, additional commands and unknown serialization are refused.
Captured enabled/disabled state must match the snapshot's known activation link
or lack of that link. Inactive runtime state can be consistent with enabled
state; it is not converted into a shell-health pass.

With these options, exit 0 and `consistent_observations=true` mean only that the
supplied observations agree within these checks. `recognized_shape` continues
to describe the filesystem snapshot alone; any comparison refusal produces exit
1 and diagnostic reasons. Invalid option pairing produces exit 2. The existing
snapshot-only interface is unchanged. `migration_ready` always remains false.

When optional fragment provenance is supplied, its successful read outcome,
source path, hash and byte count must match the snapshot's unit bytes. A refused,
malformed or mismatched record makes the comparison fail. `fragment_bytes_match`
is true for a match, false for refused/mismatched provenance, and null for legacy
metadata-only captures. An absent hash never implies a byte match.

This does not prove capture freshness, snapshot origin or byte identity with the
manager's loaded unit. A supplied hash is evidence, not authentication of origin.
It does not enumerate higher-precedence files, additional activation paths or
live sessions. Stable private snapshots are still required. Neither input is
modified, source paths are never followed, and captured commands are never run.
This development-only path remains outside setup and packaging.

Run `PYTHONDONTWRITEBYTECODE=1 python3 -W error
tests/shell-ownership-consistency.py` for disposable consistency/refusal fixtures.

## Next bounded implementation step

Review and explicitly classify the retained real VM service's Unit, Service
and Install directives. In one bounded follow-up, define and test whether that
exact direct-launch shape can be safely recognized, with refusal cases for
changed dependency, environment, restart and activation semantics. Do not add
general systemd parsing or lifecycle mutation. A byte match alone must never
approve unknown directives. Capture freshness, full activation/session
assessment and the launcher-conflict fix remain subsequent work.
