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
