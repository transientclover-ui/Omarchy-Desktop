# Actual systemd-261 effective-property capture

These are sanitized observations from a fresh disposable guest on 2026-09-25,
using unchanged production tools from checkpoint `63503b5` (implemented at
`db7cd35`). The overlay was backed by the preserved revision-5 image and its clean
Omarchy baseline. Separate firmware and a removable USB payload/results disk
were used; there was no network device, host block device or host filesystem share.
The user unlocked the disk directly. The removable payload auto-mounted normally.

## Observed results

- Full capture and legacy collector exit 0; effective collection true; evidence
  mode 0600. All 30 Unit and 35 Service property replies were present and typed.
- The exact 386-byte unit hashes to
  `e7ed27417635e1347352cfe571a947e707f59e0cdb28dcaf8519e765a90a8703`.
  Independent before/after hashes of the unit and shell.json agreed.
- `observed.json` is the sanitized guest-produced comparison: recognized shape
  and fragment-byte match true, but exit 1 and effective/overall comparison false.
  Its sole refusal is `After`.
- Actual After contains `app.slice`, `basic.target`, `home.mount`,
  `graphical-session.target`, and `-.mount`. The contract lacks the two mounts.
  All other compared properties matched. No drop-ins or stale-manager flag were
  reported; the service was enabled but inactive/dead, with its last process
  exited at status 0. This is not a shell-health or exclusive-ownership pass.
- `changed-restart.json` was produced **offline**, changing only the copied
  effective Restart value to `always`. It retains the original After refusal
  and adds a Restart refusal; the unchanged fragment hash still matches.
- Both comparison cases keep `migration_ready=false`. No recognized set or
  production comparison rule was expanded to turn the observation into a pass.

## Dependency investigation

`dependency-origin.txt` contains a separate read-only guest query. It reports
`WorkingDirectory=!/home/test`, `WantsMountsFor=/home/test`, empty RequiresMountsFor
and RootDirectory, and loaded `/home` and `/` mount units without fragment files.
The home mount reports `/proc/self/mountinfo` as its source.

This is consistent with systemd 261 assigning the home directory to user services,
adding mount-path dependencies for that directory, and adding ordering for loaded
mounts even without mount-unit fragments. See `unit_patch_contexts`,
`unit_add_exec_dependencies` and `unit_add_mount_dependencies` in
[systemd's unit implementation](https://github.com/systemd/systemd/blob/v261/src/core/unit.c).
These supporting observations explain the refusal but do not authenticate every
edge's origin. The current collector does not capture these supporting fields as
part of its contract. Arbitrary mount dependencies must not be silently accepted.

## Files and sanitization

`capture.json` is the full capture envelope; `Unit-raw.jsonl` and
`Service-raw.jsonl` are separate repeated busctl queries in the collector's field
order. After sanitization, both repeated queries exactly match the capture's
property records. Each JSON line is reformatted, but its type/data structure is
retained. `omarchy-shell.service` contains unchanged exact bytes. `validation.json`
records the runner's exit statuses, systemd version, mode and unchanged hashes.

Sanitization replaces `/home/omarchytest` with `/home/test`, the command PID with
1234, and human-readable start/stop times with midnight on the same date. All four
ExecStartEx runtime timestamps are zeroed; code/status and all configuration values
are preserved. Only the capture envelope's `sanitized` flag changes to true.
The fixture hashes refer to the original unit bytes, which needed no redaction.
No account password, disk passphrase or shell.json contents are retained here.

The snapshot activation link was constructed for comparison, not collected as a
complete activation inventory. Capture, fragment hashing, diagnostic queries and
comparison were sequential observations, not an atomic snapshot. The fixture
cannot establish freshness, process configuration, Plasma compatibility, startup
health or absence of other launchers.

## Cleanup and replay

The payload was unmounted before native guest poweroff. QEMU exited with 0;
offline QCOW2 and read-only payload-filesystem checks passed. The preserved clean
baseline retained its recorded SHA-256. Private runner, raw evidence and disposable
images remain under ignored `evidence/effective-properties-resume-20260925/`.

Run `PYTHONDONTWRITEBYTECODE=1 python3 -W error tests/shell-effective-vm-replay.py`.
The formerly skipped scaffold now requires these real fixtures and checks both
full reports plus typed-query replay, exact hashes, and unchanged input files.
The comparison runs with an empty PATH; property queries are mocked, not live.
