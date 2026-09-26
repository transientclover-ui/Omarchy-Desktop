# Actual systemd-261 mount-context capture

Sanitized observations from a fresh disposable VM on 2026-09-26, using unchanged
capture/comparison tools from `2cf4018`. The new overlay was backed by the preserved
revision-5 image and clean baseline, with separate firmware. No network device,
host block device or host filesystem share was attached. The user unlocked the
encrypted guest directly; no credential is retained.

## Results

Capture and legacy metadata collector returned 0 under systemd 261 (261.2-1-arch).
All 65 effective properties and all 29 supplementary properties were collected.
Six additional independent queries exactly matched the supplementary capture,
including ordering of array entries. Evidence mode was 0600.

The guest-produced `observed.json` reports mount_context_consistent=true with no
supplementary reasons. Overall comparison still exits 1 and refuses only After;
effective_properties_match and consistent_observations are false, while
migration_ready remains false. No recognition contract was changed.

Observed supplementary settings:

- After contains graphical-session.target, home.mount, basic.target, -.mount and
  app.slice. RequiresMountsFor is empty; WantsMountsFor contains /home/test.
- WorkingDirectory is !/home/test; RootDirectory and RootImage are empty.
- Shell/home/root units are loaded, non-transient, with no reported drop-ins or
  pending reload. Shell fragment matches the captured user unit.
- Home/root mounts have empty fragment paths and Where=/home or /. Home SourcePath
  is /proc/self/mountinfo; root SourcePath is empty.

The service was active/running during this capture (unlike the earlier effective
fixture), but this is not a shell-health or exclusive-ownership verdict. The known
extra bar remained visible. No service lifecycle action was used to create a
comparison case. The 386-byte unit SHA-256 remains
`e7ed27417635e1347352cfe571a947e707f59e0cdb28dcaf8519e765a90a8703`;
independent before/after hashes of the unit and shell.json agreed.

## Provenance and limitations

`capture.json` is the complete capture envelope. Six `*-raw.jsonl` files are
separate repeated guest busctl replies in the corresponding GROUPS field order.
`validation.json` records runner statuses, version, output mode and unchanged
hashes. `omarchy-shell.service` preserves exact bytes. `observed.json` is the
sanitized guest comparison. `changed-home.json` and `changed-restart.json` are
**offline-only** comparisons mutating, respectively, HomeMount.Where to /other
and effective Restart to always. Both retain the After refusal and make the
supplementary result false. No live unit or mount was altered for these cases.

Sanitization replaces /home/omarchytest with /home/test in values and keys, command
PID with 1234, human-readable runtime times with midnight on the same date, and
ExecStartEx's four runtime timestamps with zero. Configuration values and runtime
exit codes are unchanged. The envelope's sanitized flag becomes true. JSON is
reformatted; unit bytes are not. No shell.json contents are retained.

The activation symlink is constructed in the comparison snapshot; it is not a
complete captured activation inventory. Queries and hashes were sequential, not
atomic. This evidence does not prove implicit dependency origins, home identity,
freshness, manager-loaded bytes, process environment, Plasma compatibility or the
absence of competing launchers. Equivalent explicit settings can yield the same
reported configuration. The scope is validation of the fixed capture and its
conservative diagnostic result on this guest.

## Harness correction and cleanup

The initial runner stopped at results-directory creation because the first USB
payload root was not writable. No capture ran on that attempt. A second disposable
USB disk was prepared with a writable root before attachment; the guest copied
the same payload there and ran successfully. Result directory and capture remained
0700/0600. Both disks were unmounted before native guest poweroff; QEMU exited 0.
Offline QCOW2 and read-only results-filesystem checks passed. Baseline SHA-256
before/after stayed `844be5c310a5750902c40d1ab95fb5144b6788b29cbfa7d3b96b29aaa253c4c0`.
Private runner, raw evidence and disposable images remain under ignored
`evidence/mount-context-20260926/`.

## Replay

Run `PYTHONDONTWRITEBYTECODE=1 python3 -W error tests/shell-mount-vm-replay.py`.
Four tests check provenance/sanitization, all six actual typed replies, truncated
replies for each group, and three complete comparisons. Comparisons run with an
empty PATH, queries are mocked, and fixture/snapshot bytes and metadata remain
unchanged. No manager is contacted by replay tests.
