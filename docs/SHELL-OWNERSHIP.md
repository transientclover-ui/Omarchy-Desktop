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

The second recognized shape is the exact 14-line service retained in
`tests/fixtures/shell-metadata/fragment-261/omarchy-shell.service`. Its literal
description, directive order and values are fixed; this is not a general unit
parser. Both shapes permit blank lines, full-line comments, surrounding ASCII
space/tab and CRLF. Unicode line separators/whitespace are not normalized.

Classification of the second shape (reviewed against the installed systemd
unit/service/exec manuals):

| Directive | Meaning and recognition limit |
| --- | --- |
| `Description` | Fixed descriptive label; no arbitrary descriptions accepted yet |
| `After=graphical-session.target` | Ordering only; does not pull in a session or identify Plasma |
| `PartOf=graphical-session.target` | Propagates target stop/restart to this service; does not establish exclusive ownership |
| `ConditionEnvironment=WAYLAND_DISPLAY` | Tests presence in the manager environment; may be stale and is not session proof |
| `Type=simple` | Direct process startup without a shell-readiness handshake |
| Two `Environment` assignments | Passes exactly `QS_DISABLE_FILE_WATCHER=1` and `QS_NO_RELOAD_POPUP=1`; no inference about plugin compatibility |
| `ExecStart` | Same fixed Quickshell command as the minimal fixture |
| `Restart=on-failure`, `RestartSec=3` | Failure restart policy with a three-second delay; does not eliminate duplicate launchers |
| `WantedBy=graphical-session.target` | Install-time activation intent; actual snapshot link and captured enablement are checked separately |

Changed/missing/duplicate/reordered directives, wrappers, resets and additional
settings are refused, even if a supplied fragment hash matches. Recognition does
not establish the manager's loaded dependency/environment/restart values; the
default collector does not query those properties. The opt-in typed comparison
below assesses a bounded subset; it still does not authorize lifecycle changes.

The unit must be a regular
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
and comment-only snapshot mismatch detection. At capture time the actual VM unit was outside the recognized minimal shape,
so the historical reports refused overall consistency despite matching bytes.
Those reports remain unchanged. The current offline replay recognizes the reviewed
exact shape and accepts matching observations, while still refusing changed bytes; see `tests/fixtures/shell-metadata/README.md`. This does not validate
fresh live-manager consistency, Plasma behavior or exclusive ownership.

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

## Opt-in effective-property comparison

Capture on a disposable guest using the existing runner:

```bash
python3 tools/capture-shell-ownership-metadata.py /private/guest-directory/effective.json \
  --hash-fragment --effective-properties
```

Then compare a stable snapshot offline:

```bash
python3 tools/shell-ownership-inventory.py SNAPSHOT \
  --capture /private/guest-directory/effective.json \
  --source-unit-directory /home/test/.config/systemd/user --require-effective
```

Use the actual source directory (or consistently sanitized mapping), as above.
The source path is never opened during comparison. The original capture and
snapshot-only interfaces remain unchanged. Recognizing the full unit adds
`unit_shape=retained-vm-v1` to inventory output.

`--effective-properties` adds an `effective` record to the private capture. The
new helper issues two bounded `busctl --user --json=short get-property` commands,
for explicitly allowlisted Unit and Service fields on the fixed encoded
`omarchy-shell.service` object. Each command has a five-second total timeout;
individual properties are separate D-Bus Get calls, **not an atomic snapshot**.
There is no GetAll, LoadUnit, environment-file read, command execution, manager
reload or service lifecycle call. Existing systemctl metadata queries still run.

Typed reads avoid inferring empty values from omitted `systemctl show` output:
in systemd 261, empty structured arrays such as EnvironmentFiles can be omitted
by its printer. Typed empty arrays are distinct from missing replies. The
collector rejects missing/extra rows, duplicate JSON keys, wrong signatures and
invalid primitive data. Unknown properties, missing busctl, denied queries and
timeouts produce incomplete evidence and capture exit 1. The original
`collector_exit_status` stays independent; `capture_exit_status` covers either
optional collection failure. Exit 0 means collected, not matched. The assessor
checks structured values and semantics offline. Nothing reads environment-file
contents, including optional or missing files.

The comparison requires the exact retained VM shape, successful full capture,
matching fragment hash/size/path, and all original metadata/snapshot checks.
Identity and fragment path must agree across observations; generated sources,
transient units, drop-ins and NeedDaemonReload are refused. A supplied effective
record is always checked even without `--require-effective`. With that flag,
legacy captures refuse rather than imply effective-property validation. Without
it, legacy captures retain their previous limited behavior and have no
`effective_properties_match` field.

The bounded `retained-vm-v1` contract checks:

| Group | Required effective values |
| --- | --- |
| Dependencies | DefaultDependencies true; After app.slice/basic.target/graphical-session.target; Requires app.slice/basic.target; Before and Conflicts shutdown.target; PartOf graphical-session.target |
| Other relationships | Empty Wants, Requisite, BindsTo, Upholds, OnFailure, OnSuccess, stop/reload propagation and JoinsNamespaceOf |
| Conditions | Exactly the positive, non-trigger WAYLAND_DISPLAY presence condition; no asserts. Its runtime result may be untested, passed or failed; none is a health or session-identity claim |
| Environment | Exactly the two reviewed assignments, order-independent and unique; empty EnvironmentFiles, PassEnvironment and UnsetEnvironment |
| Execution | Type simple, ExitType main, no RemainAfterExit, PIDFile or BusName; app.slice; one exact ExecStartEx path/argv with no execution flags; no condition/pre/post/reload/reload-post/stop commands |
| Restart | on-failure, normal mode, 3,000,000 microseconds; zero backoff steps, infinite maximum delay; no custom success/prevent/force exit-status sets |
| Related defaults | Start limit 5 per 10 seconds with no action; no failure/success action; 90-second start/stop timeouts, unlimited runtime, no watchdog; control-group kill mode, SIGTERM for stop/restart, final SIGKILL enabled |

Unordered string sets may reorder, but duplicates or extra values refuse.
Durations are typed integer microseconds; infinity is unsigned 64-bit maximum.
No shell quoting or human time formatting is guessed. Command runtime timestamps,
PID and exit results are type/range checked, not interpreted as proof of health.

Explicit values come from the retained unit. **Implicit dependencies and related
defaults are a source-reviewed candidate contract, not new VM observations.**
Different legitimate manager defaults or reverse dependencies can conservatively
refuse; do not silently broaden the contract to obtain a pass. Reference points:
[systemd 261 user-service defaults](https://github.com/systemd/systemd/blob/v261/src/core/service.c),
[slice dependencies](https://github.com/systemd/systemd/blob/v261/src/core/unit.c),
[Unit properties](https://github.com/systemd/systemd/blob/v261/src/core/dbus-unit.c),
[Service properties](https://github.com/systemd/systemd/blob/v261/src/core/dbus-service.c),
[environment properties](https://github.com/systemd/systemd/blob/v261/src/core/dbus-execute.c),
and [show serialization](https://github.com/systemd/systemd/blob/v261/src/systemctl/systemctl-show.c).

`effective_properties_match=true` and exit 0 mean all these supplied observations
agree within this contract. `migration_ready` remains false. This is not a full
unit-equivalence proof, a current-process configuration check, or authority to
transfer ownership. Inherited manager/process environment, resource/sandbox
settings outside the allowlist, freshness, dependency origins, complete search
paths/activation sources, overlapping sessions and duplicate launchers remain
unassessed. Hashing does not authenticate evidence or reveal loaded unit bytes.

Validation: `PYTHONDONTWRITEBYTECODE=1 python3 -W error
tests/shell-effective-properties.py`. The typed fixture is explicitly synthetic;
it is combined with copies of historical metadata and fragment evidence only
inside disposable tests. A separate real systemd-261 capture now validates all
65 typed replies and full fragment capture. Its exact service is conservatively
refused because After also includes `home.mount` and `-.mount`; all other compared
properties match. The candidate contract remains unchanged. See the
[guest evidence and dependency investigation](../tests/fixtures/shell-effective/systemd-261/README.md).

`tests/shell-effective-vm-replay.py` now runs without pending-evidence skips. It
replays typed replies, the guest-produced refusal, and an offline Restart mutation
that adds a second refusal despite matching fragment bytes. The guest service was
enabled but inactive; neither capture success nor the other matching properties
establish shell health. Earlier VM fixtures remain unchanged.

## Supplementary mount-context evidence

The optional development capture adds six fixed, read-only typed queries (29
properties) for omarchy-shell.service, home.mount and -.mount:

```sh
python3 tools/capture-shell-ownership-metadata.py /private/guest-directory/mount.json \
  --hash-fragment --effective-properties --mount-context
python3 tools/shell-ownership-inventory.py /private/offline-snapshot \
  --capture /private/guest-directory/mount.json \
  --source-unit-directory /home/test/.config/systemd/user \
  --require-effective --mount-home /home/test
```

Run capture only in the authorized disposable guest; comparison is offline.
Both existing capture flags are required. Incomplete prerequisite capture skips
these additional queries. Each query has a five-second timeout (up to 30 seconds
additional); objects and property lists are fixed, with no discovered paths,
unit loading or lifecycle commands. Failed queries preserve partial evidence and
make capture fail. The output retains exclusive creation and mode 0600.

The new `mount_context` envelope contains typed shell identity, After,
RequiresMountsFor, WantsMountsFor, WorkingDirectory, RootDirectory and RootImage;
home/root identity, fragment/source paths, drop-ins, reload/transient state; and
both mount Where values. Missing, extra, malformed and failed records refuse.

`--mount-home` is an explicit evidence mapping, never a host account lookup. The
bounded candidate supports `/home/` followed by 1–64 ASCII letters, digits,
underscores or hyphens, with no leading hyphen or digit. It requires the matching
home-relative .config/systemd/user fragment path. Other layouts are unsupported.
The shell identity and After must agree across both captures, with matching
snapshot/fragment evidence and no effective disagreement other than the existing
After refusal. The supplemental expectations are:

- Exactly app.slice, basic.target, graphical-session.target, home.mount and
  -.mount in After; no duplicate or unrelated ordering entries.
- Empty RequiresMountsFor and WantsMountsFor containing only the mapped home.
- WorkingDirectory equal to `!` plus that home; empty RootDirectory/RootImage.
  The prefix is systemd's missing-directory-allowed serialization, as shown in
  [systemd v261's property getter](https://github.com/systemd/systemd/blob/v261/src/core/dbus-execute.c).
- Loaded, non-transient shell/home/root units with no reported drop-ins or
  pending reload. Both mounts have empty FragmentPath; the home SourcePath is
  /proc/self/mountinfo, the root SourcePath is empty, and Where is /home or /.

`mount_context_consistent=true` means only these supplementary observations
agree. **Overall consistency and effective-property match remain false**, the
After refusal remains, comparison exits 1, and migration_ready stays false.
Supplying supplementary evidence without a supported home mapping also refuses;
it is never silently ignored.

This is not proof of implicit dependency origin: explicit declarations can yield
equivalent loaded values. Home identity, capture freshness, changes between
queries and manager-loaded bytes remain unproven. No dependency is newly allowed.
The grouped capture has now been validated in a fresh systemd-261 disposable guest.
All 29 supplementary replies matched separate repeated queries, and the actual
comparison reported supplementary agreement while retaining the After refusal.
See [actual mount-context evidence](../tests/fixtures/shell-mount/systemd-261/README.md)
and `tests/shell-mount-vm-replay.py` for provenance, limitations and replay. Tests in
`tests/shell-mount-context.py` combine explicitly synthetic supplementary records
with the unchanged retained guest capture and text diagnostics; they do not claim
new real VM evidence. They cover every property's omission/type/value changes,
query failures, cross-capture disagreement and preservation of refusal behavior.

## Next bounded implementation step

Add bounded capture-coherence checks around the sequential observations, with
adversarial fixtures for unit/configuration changes between reads. Document what
before/after agreement can and cannot establish; it must not imply an atomic
snapshot or prove dependency origins. Keep the After refusal and migration
readiness false. Stop before live ownership, duplicate-launcher resolution or
release validation.
