# Display Power-Cycle Protection — investigation checkpoint

Status: **not implemented or available as a toggle**. The existing host workaround
has been located, but its effective recovery action has not been established.
This checkpoint preserves the evidence and reproduces its failure/no-op paths in
isolated tests. It does not replace, repair, adopt or disable the host workaround.

The [KDE Wayland follow-up](DISPLAY-POWER-CYCLE-KDE.md) now traces the native
hotplug/restoration path and recommends a native-first diagnostic approach. The
original workaround still has no established causal role in successful recovery.

## Original problem

The user uses a TV as the primary desktop display. Switching it off with its remote
while the computer and KDE session keep running could leave a black screen or
failed recovery when the TV was turned back on. The user reports that an existing
workaround fixed this. No power-cycle was performed during this investigation.

An independently powered HDMI display can become unavailable to the GPU while the
session remains active. Connection detection and display-mode recovery are distinct
from keeping the computer awake. Linux DRM exposes connector status and hotplug
notifications; a bad link can require a new modeset to restore pixels. This is a
plausible failure class, not a diagnosis of the particular TV. See the
[kernel KMS connector and link-status documentation](https://docs.kernel.org/gpu/drm-kms.html).
Not every TV or gaming display needs a workaround; cable, GPU, driver, firmware
and display standby behavior matter.

## Discovered host configuration

| File or setting | Observed role |
| --- | --- |
| `~/.local/bin/recover-tv-display.sh` | Recovery attempt for `/sys/class/drm/card1-HDMI-A-1`; no generic connector selection |
| `~/.config/systemd/user/recover-tv-display.service` | Wayland-conditioned oneshot executing that script, After/PartOf graphical-session.target |
| `/etc/udev/rules.d/99-recover-tv-display.rules` | Root-owned active rule; user supplied its contents after privileged read was unavailable |
| `~/.config/udev/rules.d/99-recover-tv-display.rules` | Older copy with malformed DBus environment assignment; not a standard system udev rule directory |
| `/etc/udev/rules.d/99-recover-tv-display.rules.bak.*` | Backup files found by name only; contents not read, not active `.rules` files |
| `~/.config/powerdevilrc` | Idle dimming, idle display-off and automatic suspend disabled; separate from proving hotplug recovery |

The supplied active rule matches ACTION=change, SUBSYSTEM=drm and
KERNEL=card1-HDMI-A-1. It sets DISPLAY=:0, XDG_RUNTIME_DIR=/run/user/1000 and
DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus, then calls systemd-cat with
the script's absolute home path. It does **not** start the user service, set HOME,
or switch execution to the desktop user. Copying a system-triggered invocation of
a user-writable script into a distribution is not an acceptable ownership model.

The service is currently loaded, inactive, with UnitFileState=indirect and no
reported drop-ins. No activation link for it was found under the inspected user
`*.wants` directories; this is not a complete activation audit. Historical service
runs exist. Recognition of these files is evidence only, not adoption authorization.

The connector is currently connected through amdgpu. The inspected kernel command
line and readable module configuration did not expose an EDID/forced-connector fix.
This was a targeted investigation, not proof that no other mechanism exists.

## What the script actually does

1. Require HOME while constructing its log path, before any connector work.
2. Read connector status; if a writable power_mode file exists, write `on` once.
   Despite the comments, this is not an off/on cycle or a verified EDID reprobe.
3. Restart `plasmashell` only if that exact user service is active.
4. If `qdbus` exists, introspect `/Outputs` on org.kde.KWin; no output-changing
   method is invoked by that command.
5. If `kscreen_doctor` exists, invoke it with `--apply-current`.
6. Sleep three seconds and report success when status reads connected. It exits
   zero even when the connector still reports disconnected.

The current host lacks connector power_mode, plasmashell.service, qdbus and
kscreen_doctor. It instead has an active plasma-plasmashell.service, qdbus6 and
kscreen-doctor. The upstream [KScreen command definition](https://github.com/KDE/libkscreen/blob/master/src/doctor/main.cpp)
does not define `--apply-current`. Renaming commands would therefore not be a
validated preservation of the original behavior.

Historical user-service logs on September 21 show the restart and display-tool
steps skipped, with the connector already connected. A September 22 hotplug log
records `HOME: unbound variable`. The supplied rule is consistent with that failure.
These observations do not establish the action responsible for the user's working
recovery. They also do not prove that recovery never worked or that the current
TV needs any additional intervention.

System udev execution is not a normal desktop session. Its rules and RUN sandbox
have specific execution constraints; see [systemd's udev specification](https://github.com/systemd/systemd/blob/v261/man/udev.xml).
No rule reload, trigger, service restart or display probe with side effects was run.

## Ownership and integration boundary

All host files, services, environment, display state and desktop settings remain
untouched. The repository contains non-executable `.txt` evidence, observation
metadata and isolated tests only. No setup/uninstall/package/profile change was
made. There is nothing new to enable, disable or roll back on the host.

The intended optional feature name remains **Display Power-Cycle Protection**.
Its future description should explain that it is for TVs and other independently
powered displays that have this problem, not a requirement for all displays.
The existing Omarchy menu extension is the appropriate control location once the
actual behavior is known; no inert or misleading checkbox is shipped now.

Before implementation, establish the working action and event/session context.
Only then define a narrow opt-in feature that:

- isolates connector and user/session mapping instead of embedding card1, UID
  1000, DISPLAY=:0 or a particular home directory;
- preserves equivalent external setups without claiming or duplicating them;
- refuses unknown scripts, conflicting triggers, masks, overrides or ambiguous
  graphical sessions rather than replacing them;
- records only Frankenstein-owned changes, checks for edits before removal, and
  reverses those changes without altering pre-existing or intentionally disabled
  choices;
- remains independent of shell profiles, with Plasma Wayland, optional bar/widgets
  and menu-only defaults unchanged.

Clean enable/disable, rollback, idempotence, equivalent-configuration preservation,
conflict refusal and UI/package integration tests are **not implemented**, because
the enable/disable contract cannot yet be derived from a verified working action.

## Evidence, troubleshooting and next step

[Retained fixtures](../tests/fixtures/display-power-cycle/host-20260926/README.md)
distinguish directly read files, a user-provided rule excerpt and observations.
Five isolated tests reproduce missing HOME, skipped actions despite a success
message, disconnected zero-exit behavior, and gated actions against fakes. They
never run the original host script or contact a real manager/display.

Do not treat the script's success message or exit status as proof of recovery.
For a subsequent read-only investigation, correlate an already-recorded successful
recovery with connector/driver and session logs, and identify whether another
script, setting or historical revision was the actual fix. No forced power-cycle
is needed for that step. Keep the current host workaround intact. Actual hardware
recovery, event delivery, correct session routing and reversibility remain
unvalidated; a VM cannot certify a physical television's power-cycle behavior.
