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

## Next bounded implementation step

Add a read-only ownership inventory with disposable fixtures for one recognized
service shape and rejection cases for alternate activation/overrides. It should
produce a reviewable assessment only. Do not add lifecycle mutation or expose a
managed setup option until that supported boundary is established.
