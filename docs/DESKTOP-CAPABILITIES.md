# Desktop capabilities and action providers

The version 1 runtime registry is available as `frankenstein capabilities` or
`frankenstein-capabilities inspect`. Both are read-only. Preview a fixed action
with `frankenstein action screenshot --plan`; omit `--plan` to dispatch it.
No configuration, service enablement, plugin installation, or downloaded code is
performed by this interface. Existing user widgets and shell configuration are untouched.

## Session and evidence contract

`session-name` only normalizes colon-separated desktop tokens: KDE and Other:KDE
become plasma; Hyprland becomes hyprland; GNOME becomes gnome. It is a display/menu
hint, **not evidence that an action can run**. Multiple known desktop tokens are
ambiguous. The shell adapter and restart wrapper share this normalization.

Runtime detection requires Wayland type, a connectable user-owned Wayland socket,
and an active same-user logind session. Plasma additionally requires a KWin D-Bus
owner matching the Wayland socket's kernel peer PID, directly or through the
known kwin_wayland_wrapper parent. Hyprland requires a user-owned instance socket, an instances entry matching
both the signature and Wayland display, and responsive monitor IPC. With no logind
record, Hyprland can use this explicit instance evidence; Plasma fails closed.
Conflicting environment/logind identities or simultaneous compositor providers
block routing. The user manager environment is never borrowed. Detection runs
fresh for each request, so session changes are not cached. Missing XDG session IDs,
permissions, inaccessible bus or utilities produce an explicit unknown/unavailable
state. A session change between detection and execution remains possible: this is
not an atomic session lock. Simultaneous sessions sharing a user bus are treated
conservatively; do not infer a Plasma display from an arbitrary KWin owner alone.

Each subprocess probe has a two-second deadline; socket connection has a 250 ms
deadline. Settings support requires both the launcher and the installed KCM module
listing. Action argv is fixed; arguments are never interpreted as shell code.
Bounded actions have a five-second deadline. GUI/interactive providers launch
independently with detached I/O and report `dispatched`, which does not prove
successful completion. Exit 3 means unsupported/unavailable provider; exit 4
means dispatch failure/timeout. No arbitrary IPC methods or executable paths are
accepted by the action API. Executables come from the caller's trusted PATH,
preserving existing user wrappers.

## Capability registry and compatibility matrix

| Capability | Plasma Wayland provider | Hyprland provider | Scope/limitations |
|---|---|---|---|
| notifications | Existing session bus owner + notify-send | Existing session bus owner + notify-send | Reports unique bus owner; registry only, never takes ownership |
| polkit | Observed agent PIDs | Observed agent PIDs | Registration remains unknown; never starts another agent |
| locking | ScreenSaver D-Bus Lock | Original omarchy-system-lock | Hyprland requires enabled Omarchy lock plugin |
| screenshots | Spectacle | Original omarchy-capture-screenshot | Hyprland picker/capture utilities checked; completion requires interaction |
| clipboard | wl-copy / wl-paste | wl-copy / wl-paste | Registry only; history and synthetic paste need separate adapters |
| monitors | kcm_kscreen | Original monitors.lua config editor | Opens settings; does not change outputs |
| workspaces | kcm_kwin_virtualdesktops | hyprctl -j workspaces | KDE settings versus Hyprland query; no generic switch action |
| night_light | kcm_nightlight | Original omarchy-toggle-nightlight | KDE settings versus original Hyprland toggle; distinct semantics |
| shortcuts | kcm_keys | Original bindings.lua config editor | No synthetic shortcut dispatch |
| input | kcm_mouse | Original input.lua config editor | Mouse settings, not all input devices |
| compositor_ipc | Verified KWin bus owner | Responsive exact Hyprland instance | Registry only; no arbitrary calls |

Supported actions: lock/locking, screenshot/screenshots, displays/monitors,
shortcuts, input, night-light/night_light, workspaces. Other registry capabilities
return explicit unsupported action results. GNOME is identified but has no adapter.
Capabilities express observed prerequisites, not complete end-to-end certification.
In particular wl-clipboard permissions, screenshot interaction and downstream
Omarchy dependencies can still fail after dispatch.

## Existing integration and dependency inventory

Duplicated desktop checks exist in the shell adapter, restart wrapper, wallpaper
helper, KDE adoption helper, soft defaults and menu guards. The first two and
packaged menu hints now use this shared interface. Wallpaper/adoption/defaults
remain scoped lifecycle helpers; migrate their full runtime behavior separately
with their existing rollback/session fixtures. No host menu extension is rewritten.

The live host inventory found enabled notifications and Polkit plugins competing
with Plasma owners; plugin policy remains unchanged by this patch. Disabled
background/idle/lock/night-light/monitor/workspace plugins remain disabled.
Tutor uses hyprctl binds/dispatch, Plug uses binds/reload and writes Hyprland
configuration, and disabled Lacquer uses Hyprland options/eval/reload. Flux's widget
is enabled while fluxd.service is absent. Clipboard history uses capture watchers
and separate paste helpers; launch-or-focus and screensaver helpers use hyprctl.
Screenshots use Hyprland IPC plus picker/capture programs. Sleep-lock and internal
monitor recovery units have Omarchy/Hyprland assumptions; crash diagnosis launching
uses the UWSM-oriented terminal path. These dependencies are inventory findings,
not permission to disable or rewrite their host configuration.

Next adapters:

1. Tutor: consume this JSON asynchronously, retain lessons, offer KDE shortcut
   settings, and mark unavailable workspace dispatch explicitly.
2. Plug: split installation/catalog features from compositor bindings; check
   capabilities before writing config or requesting reload. Keep Hyprland edits
   and user customizations intact.
3. Omarchy menus: merge opt-in action entries through existing extension/backup
   machinery. Offer KDE providers while retaining original Hyprland actions.
4. Ownership policy: add separate reviewed notification/Polkit plugin policy;
   agent observation alone must not authorize automatic disabling.

## Validation

`python tests/desktop-capabilities.py` covers normalized desktop lists, live-evidence
fixtures, stale/conflicting variables, repeated detection across session changes,
GNOME unsupported states, missing utilities/KCMs/bus owners/lock plugins, wrong
Hyprland display mapping, real temporary sockets, timeout handling, fixed actions,
and preview-without-dispatch. Existing session-boundary and shell-restart fixtures
verify integration behavior without live desktop mutations.

Live read-only Plasma checks verify logind/session/socket/KWin evidence, notification
bus ownership, observed KDE agent, lock bus presence and installed KCM modules.
No live lock, screenshot, clipboard content, settings launch or session switch is
performed. No Hyprland session is running on the host: its action behavior is
fixture-tested and requires later live validation. Polkit registration is explicitly
unverified. User-widget functionality is preserved by leaving widget sources and
configuration untouched; no comprehensive interactive widget certification is claimed.

Validation result for this change: all 13 focused/regression suites passed:
desktop-capabilities, session-boundaries, shell-restart, watchdog, plasma-wallpaper,
preserved-shell-health, shell-control, settings-selection, install-workflow,
preserve-shell, installer-rollback, shell-profile and kde-shell-bar. The new registry
suite has 10 tests; all eight Python unittest suites total 50 tests. Installer and
preservation scripts additionally cover packaged/standalone rollback scenarios.
Shell syntax and whitespace checks passed; all 56 package source hashes matched.
Package metadata was regenerated for 0.1.0-16; no binary package was rebuilt or
installed in this work order.
