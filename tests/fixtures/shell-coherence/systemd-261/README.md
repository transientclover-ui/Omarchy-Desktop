# Actual repeated ownership capture: systemd 261

On 2026-09-27, unchanged tools from adoption checkpoint `19cf1b9` ran against a
real systemd 261 (261.2-1-arch) user manager in a fresh disposable QEMU/KVM overlay.
The preserved revision-5 image backed the overlay; firmware was separate. No
network device, host block device or host filesystem share was attached. The user
unlocked the encrypted guest directly. Only a disposable 64-MiB ext4 USB payload
and results image was attached. No host configuration or service was changed.

## Observed results

| Case | Capture exit | Coherence agrees | Comparison exit | Migration ready |
| --- | --- | --- | --- | --- |
| Stable | 0 | true | 1 | false |
| Guest fragment comment appended between passes | 1 | false | 1 | false |

The stable comparison retained exactly the existing After refusal. Fragment bytes
matched and supplementary mount context agreed. Both captures have mode 0600.
The changed case preserved differences in all four observation groups, including
NeedDaemonReload changing from no to yes and fragment size/hash changing. Repeated
metadata was consequently incomplete; refusal included both incomplete evidence
and changed observations. Effective and mount queries themselves completed.
The existing After refusal remained. No recognition contract was broadened.

Original fragment: 386 bytes, SHA-256
`e7ed27417635e1347352cfe571a947e707f59e0cdb28dcaf8519e765a90a8703`.
Changed fragment SHA-256:
`7a843b7626dbf9eea01928d471969c6c0ae272fe66b40d050c9c46b9bb5ae7c8`.
The appended bytes were exactly `\n# Disposable coherence validation change\n`.
Original unit bytes and mtime were restored in a finally block; shell.json bytes
were unchanged. No daemon reload, service lifecycle change or package action was
used to induce the mismatch. Restoring the file does not assert restoration of
cached manager state; the disposable guest was powered off afterward.

## Reproduction and provenance

`run-guest.py` is an explicit disposable-QEMU harness, not a host command. Copy it
beside the existing `tools/*.py` into a writable disposable guest payload directory
and invoke `python3 run-guest.py --disposable-guest` as the guest desktop user.
It requires the retained unit and shell.json and exclusively creates `results`.
The stable case uses the real tools directly. For the changed case, a PATH wrapper
for busctl delegates every query to `/usr/bin/busctl` without changing its output.
After the first RootMount.Where query returns, it appends the comment before
returning that last initial-pass reply. Thus the change is deterministic between
the initial observation and repeated observation, without modifying production
capture code or fabricating manager replies. `mutation.json` records the trigger.

`stable.json` and `changed.json` contain complete two-pass envelopes;
`*-comparison.json` are actual guest comparison results. `validation.json` retains
statuses, output modes and before/after/restored hashes. `payload-sha256.json`
records the actual tools and harness delivered to this run. `omarchy-shell.service`
preserves exact original bytes. Home paths in JSON keys and values are replaced
consistently with `/home/test`, and sanitized flags are true. Runtime PID/time
values are retained as observed; no difference was normalized away. Sanitization
was checked to preserve both coherence assessment and the set of changed groups.
No shell.json contents or credentials are retained here.

The snapshot activation symlink is constructed by the harness, as in the existing
mount-context workflow; it is not a complete activation inventory. Stable
agreement is not atomicity, manager identity, loaded-byte identity, ownership,
shell health, session coverage or migration authorization. This validates one
real file/reload-state change, not every possible lifecycle race. KDE Plasma
compatibility and disabled-choice behavior remain covered separately; this run
did not exercise desktop switching or change profiles.

One terminal command initially used fish syntax in Bash and failed before the
harness ran; correcting the command started the successful run. Results were
unmounted, native guest poweroff completed and QEMU exited 0. Read-only ext4 and
QCOW2 checks passed. Backing image SHA-256 values were unchanged:

- Baseline: `844be5c310a5750902c40d1ab95fb5144b6788b29cbfa7d3b96b29aaa253c4c0`
- Revision-5: `435a47bdd846305c938f9172e2a8aa81d618144924d2be2af843e0e2a8149683`

Private images, raw results and test logs remain in ignored
`evidence/coherence-20260927/`. Replay with
`PYTHONDONTWRITEBYTECODE=1 python3 -W error tests/shell-coherence-vm-replay.py`.
Three tests validate provenance/restoration, independently recompute coherence and
reject forged agreement, and reproduce both complete comparisons with and without
`--require-coherence`. Comparison PATH is empty; no manager is contacted, and
fixture bytes remain unchanged.
