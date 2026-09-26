# Display Power-Cycle Protection: KDE Wayland decision

Investigation completed 2026-09-26, starting at `df07753`. No toggle, recovery
helper, adoption or live repair was implemented. The smallest justified mechanism
for the requested lifecycle is **KWin's existing native output management**.
An additional automatic recovery action is not yet justified by the evidence.
The user's successful recovery is real reported experience; its cause remains
unproven. Native KWin recovery is a plausible explanation, not a demonstrated cause.

## Intended behavior and old implementation

The intent is to keep the desktop session alive while an independently powered TV
is unavailable, then restore usable output when it returns. This is not identical
to preventing idle sleep or turning software DPMS back on.

The [original evidence](DISPLAY-POWER-CYCLE.md) describes a connector-specific
script, user oneshot service and system udev rule. Their intended division was an
HDMI event trigger followed by a user-desktop refresh. The actual rule bypasses
the user unit, calls the user-writable script directly, and does not establish a
normal user login environment. Its supplied runtime/bus variables do not provide
HOME; a new isolated test reproduces the early failure with those exact variables.

Other mismatches remain: the current connector has no power_mode file; the script
checks plasmashell.service instead of plasma-plasmashell.service and names qdbus
and kscreen_doctor instead of the installed qdbus6 and kscreen-doctor. Introspection
of KWin is not an output change. Neither connected status nor exit zero establishes
successful visual recovery. Correcting names alone would not establish a solution:
`--apply-current` is not defined by the reviewed
[KScreen 6.7.4 CLI](https://github.com/KDE/libkscreen/blob/v6.7.4/src/doctor/main.cpp).

The package log places these KDE versions' installation before the workaround's
file timestamps on September 18. There is no evidence here that a later KDE upgrade
made a previously correct command obsolete. Root-only rule backups remain unread;
matching earlier commands were not found in the targeted readable shell histories.
The unrelated desktop-restore backup concerns SDDM/Hyprland readiness, not HDMI
recovery. No component can currently be credited with successful recovery merely
from these files, timestamps or logs.

## Native KDE lifecycle

The upstream sources reviewed are tagged **v6.7.4**, matching the installed KDE
version numbers. Distribution patch equivalence was not established. Local package
verification reported zero altered KWin files; that verifies installed package
metadata, not exact correspondence to upstream source.

1. **Connection change:** KWin's DRM backend subscribes to DRM udev events and
   refreshes outputs for an active GPU. It already occupies the role the custom
   rule was trying to provide. It also updates outputs when a paused device resumes.
   See [DrmBackend::handleUdevEvent/updateOutputs](https://github.com/KDE/kwin/blob/v6.7.4/src/backends/drm/drm_backend.cpp).
2. **Disconnect/reconnect:** GPU output enumeration removes unavailable outputs
   and constructs newly connected ones. A reported bad link sets a forced-modeset
   flag for renegotiation. Driver reporting and a successful commit still matter;
   this cannot promise recovery from every GPU/TV failure.
   See [DrmGpu::updateOutputs](https://github.com/KDE/kwin/blob/v6.7.4/src/backends/drm/drm_gpu.cpp).
3. **Restore configuration:** KWin queries its saved setup and otherwise generates
   one. Output matching uses EDID identity/hash and, where needed, MST path and
   connector identity. The store is kwinoutputconfig.json. Reconnection is not a
   reason to delete or overwrite this file. Changed or ambiguous identity may
   prevent the expected saved setup from matching.
   See [OutputConfigurationStore](https://github.com/KDE/kwin/blob/v6.7.4/src/outputconfigurationstore.cpp).
4. **No physical screen:** Workspace maintains a placeholder output and later
   replaces it with real outputs. It applies the selected configuration and tracks
   window placement; this is not a guarantee that every application restores its
   exact geometry. New outputs normally cause a DPMS wake, with a short exception
   for recently removed DPMS-off outputs. The reviewed default grace is 2000 ms;
   changing KWIN_DPMS_WORKAROUND_TIMEOUT is not justified here.
   See [Workspace output handling](https://github.com/KDE/kwin/blob/v6.7.4/src/workspace.cpp).

A TV can report a disconnect, retain a connection while asleep, or return with
changed capabilities. These cases require different diagnosis. A session surviving
without a screen does not prove the physical HDMI link will recover. Conversely,
software DPMS-off is not proof that the TV was physically powered off.

KScreen's Wayland backend is a client of the compositor's output-management
protocol. Configuration requests have applied/failed completion, and an unchanged
configuration can produce no request. Therefore an identical enable/mode command
is not a reliable forced modeset. See [WaylandConfig::applyConfig](https://github.com/KDE/libkscreen/blob/v6.7.4/backends/kwayland/waylandconfig.cpp).
The legacy KScreen KDED module's [metadata](https://github.com/KDE/kscreen/blob/v6.7.4/kded/kscreen.json.in)
limits it to the xcb platform; it should not be installed or restarted as a Wayland
hotplug solution. Plasma panels are also not the DRM output manager: restarting
plasmashell is not equivalent to asking KWin to recover the display.

## Installed Omarchy/KDE environment

Read-only checks confirmed an active, local KDE Wayland login; active
plasma-kwin_wayland.service and plasma-plasmashell.service without reported drop-ins;
Plasma workspace/graphical targets active; and standard startplasma-wayland session
startup. The tool process itself could not resolve logind's `self`; its advertised
session ID was checked explicitly. This is not a general session-ownership proof.

Installed versions: KWin 6.7.4-7, Plasma workspace/PowerDevil 6.7.4-3,
KScreen/libkscreen 6.7.4-1, Omarchy 4.0.4-1 and systemd 261.2-1. The running kernel
is 7.2.3-zen1-3-zen, despite linux-omarchy also being installed. Selected KWin-process
environment checks found KDE/Wayland and no KWIN_* overrides; user-manager variables
alone would not have been enough to establish the process environment.

A read-only `kscreen-doctor --json` query through the Wayland Qt platform returned
one HDMI-A-1 output, connected and enabled, current mode ID 1, scale 1. This describes
only the moment queried. The saved store has two historical records for this
connector with different EDID identities/hashes; this is a reason to diagnose
identity during a future episode, not proof that power-cycling changes the EDID.
No raw EDID or monitor identity values are retained.

Omarchy's installed monitor panel issues `hyprctl keyword monitor` commands, which
are not KWin controls. The host already disables omarchy.monitor, idle, lock,
nightlight and workspaces plugins. Preserve these choices, without disabling the
optional top bar or unrelated widgets. Omarchy's sleep-lock service is scoped to
the generic graphical target and conditioned on environment; those conditions are
not KDE session ownership or evidence of a TV-reconnect function. PowerDevil's
existing idle-off/suspend choices must also be preserved.

An eventual helper must be an unprivileged client of the verified active local
KDE Wayland session. Merely seeing WAYLAND_DISPLAY in a persistent user manager,
ordering After=graphical-session.target, or fixing UID 1000 does not establish that
session. A new generic user service could otherwise run under Hyprland or a stale
session. No root udev runner, GPU reset, KWin restart, forced EDID, kernel flag,
SDDM change or new display-configuration owner is justified by this investigation.

## Recommended Frankenstein boundary

For a healthy reconnect, leave the native chain in control. Do not offer a toggle
that merely claims to enable behavior KWin already supplies. Do not adopt or remove
external recovery files automatically; recognition must preserve them and report
uncertainty/conflicts without creating a second trigger.

If a future optional fallback is needed, first capture a failed episode that
separates these cases:

| Observation after return | Defensible next step |
| --- | --- |
| Connector still absent/disconnected | Diagnose driver, link and device detection; no userspace mode can target an absent output |
| Output present and intentionally disabled | Preserve the choice; no automatic enable |
| Previously enabled output returns disabled unexpectedly | Candidate for an explicit, scoped KScreen configuration request after native settling, only with reliable identity and user policy |
| Output enabled but DPMS off | Distinguish intentional idle/lock policy before considering a wake; do not override it globally |
| Output enabled, DPMS on, image black | Gather link/commit diagnostics; neither identical reapply nor Plasma restart is a proven fix |
| Identity changed, multiple sessions, or conflicting trigger | Refuse action and retain evidence |

These are decision boundaries, not an implemented recovery algorithm. A potential
retry must be bounded, coalesced, session-scoped and conditional on a demonstrated
failure; it must preserve current layout, modes, HDR/VRR, disabled choices and
external ownership. Disable should remove only Frankenstein-owned state, with
edit/conflict detection. No new automatic action has sufficient evidence to be
selected now.

**Next smallest implementation task:** build an explicitly invoked read-only
`display-check` diagnostic (no toggle, daemon or corrective command) that records
sanitized session, connector, KScreen, DPMS and legacy-trigger facts with timestamps
and refusal on incomplete/ambiguous evidence. Test it with absent-output,
intentional-disable, changed-identity and stale-session fixtures. Its purpose is
to distinguish these cases during naturally occurring observations, not certify
pixels on screen. Do not run a disruptive hardware experiment as part of that task.

## Validation and remaining unknowns

- **Existing real machine:** user reports successful recovery; current read-only
  queries show a usable configuration. Old logs establish a script failure and
  skipped actions, not the cause of successful recovery. KWin error messages lack
  correlation with a confirmed TV event. Some no-output messages came from
  kscreenlocker_greet, not KWin; they must not be relabelled as compositor recovery.
- **Software/configuration:** version-matched source review, installed units,
  selected environment, package metadata and read-only output query support the
  native lifecycle described above. They do not prove distro-source identity or
  a particular physical reconnect outcome.
- **Isolated tests:** six retained-script diagnostics, profile/settings/preservation
  regressions. The new case reproduces missing HOME with the supplied udev variables.
- **VM/simulation:** none newly performed. Fake commands/files in tests do not
  model real DRM/EDID timing, and no upstream KWin tests were built or run.
- **Unverified hardware:** reliable event delivery, EDID stability, link training,
  actual pixels, complete user layout restoration and the causal contribution of
  the old workaround. No deliberate power-cycle or active-session disruption occurred.

[Sanitized observations and source manifest](../tests/fixtures/display-power-cycle/plasma-wayland-20260926/README.md)
keep these evidence classes separate. Host files, services, udev, KDE settings,
packages, repositories and SDDM remain untouched. This completes the investigation;
implementation of Display Power-Cycle Protection remains deferred.
