# Omarchy Desktop Compatibility Journal

## 2026-09-22 — Clean Omarchy baseline established

### VM boundary and configuration

- **VM manager:** direct `qemu-system-x86_64` with KVM acceleration (not libvirt).
- **VM name:** `Omarchy desktop compatibility lab`.
- **Resources:** Q35/UEFI, 4 virtual CPUs, 4 GiB RAM, virtio VGA, user-mode virtual networking.
- **Installation disk:** `omarchy-kde.qcow2`, QCOW2 virtual size 40 GiB, attached to the guest as `/dev/vda`.
- **Safety verification:** QEMU was passed only the VM QCOW2 image, the Omarchy ISO, and OVMF files. No host block device is attached or was modified.
- **Installer image:** `omarchy-4.0.4.iso`; SHA-256 verification passed before installation.

### Installation choices

- Keyboard: English (US)
- Test account: `omarchytest` (temporary VM-only credentials; password intentionally not recorded)
- Display name: Omarchy Test
- Git email: skipped
- Hostname: `omarchy`
- Time zone: `America/New_York`
- Installation target: the sole installer disk, `/dev/vda (40G)`
- Encryption: enabled by the installer; the first boot correctly required the VM's LUKS root-volume passphrase.

### Installation and first boot

- The installer completed and offered **Reboot Now**.
- UEFI subsequently booted Limine from the virtual disk's EFI partition, rather than the installer ISO.
- The early boot log reported `Unable to resume from device '/dev/mapper/root' ... continuing boot process`; boot continued normally. This is a no-hibernation resume message, not an installation failure.
- Omarchy reached its normal Hyprland desktop. The wallpaper, top bar, onboarding notifications, pointer, and a launched terminal rendered normally.
- Guest networking is active through QEMU user networking: interface `enp0s3` received `10.0.2.15/24`.
- External connectivity was verified with one successful ICMP reply from
  `1.1.1.1` (0% loss, approximately 8.5 ms).

### Baseline software and session stack

| Component | Observed baseline |
| --- | --- |
| Omarchy | `4.0.4-1` |
| Kernel | `7.25.3-omarchy` |
| Hyprland | `0.56.2` (build date Wed Aug 5 14:11:23 2026) |
| UWSM | `0.26.7` |
| Display manager | `sddm.service`, enabled and active |
| User graphical target | `graphical-session.target`, active |

SDDM selected `/usr/local/share/wayland-sessions/omarchy.desktop` and launched the graphical session with:

```text
uwsm start -g -1 -e -D Hyprland hyprland.desktop
```

The baseline session list showed `Hyprland-UWSM.desktop` and `hyprland.desktop`; `/usr/share/xsessions` was absent. The active Omarchy session entry is supplied from `/usr/local/share/wayland-sessions/omarchy.desktop`.

Relevant enabled system services/sockets observed:

- `sddm.service`
- `NetworkManager.service`
- `NetworkManager-dispatcher.service`
- `cups.path` and `cups.socket`
- `docker.socket`

### Baseline snapshot

QEMU cannot create an internal snapshot while the writable `OVMF_VARS.fd`
pflash device is attached. A verified disk-only external snapshot was created
instead:

- **Immutable clean baseline:** `omarchy-kde.qcow2` (40 GiB virtual disk;
  approximately 6.4 GiB host allocation after installation)
- **Current writable overlay:** `omarchy-kde-after-baseline.qcow2`
- **Backing relationship:** the overlay is QCOW2 format and references
  `omarchy-kde.qcow2` as its backing file.
- **Launcher:** `start-vm.sh` now boots the writable overlay, preserving the
  clean baseline for restoration or further throwaway overlays.
- A `qemu-img check -U` attempted while QEMU still had the overlay open
  reported one leaked cluster (wasted space only). It was deliberately not
  repaired live; QMP reported `drive0` I/O status `ok`, the overlay and
  backing image both report `corrupt: false`, and the desktop remained
  responsive. Run an offline image check before any future repair.

### Compatibility-test status

No additional desktop environment, display manager, or session package has been installed. Host SDDM, KDE, Hyprland, disks, and configuration were not changed.

## 2026-09-22 — KDE coexistence architecture investigation (read-only)

### SDDM ownership and default-session selection

Omarchy uses the system `sddm.service`; it does not replace SDDM with a custom
display manager. The observed configuration is:

```ini
# /etc/sddm.conf.d/10-wayland.conf
[General]
DisplayServer=wayland

[Wayland]
CompositorCommand=start-hyprland -- --config /usr/share/sddm/hyprland.lua

# /etc/sddm.conf.d/99-omarchy-login.conf
[Theme]
Current=omarchy

# /etc/sddm.conf.d/autologin.conf
[Users]
RememberLastUser=true
RememberLastSession=true

[Autologin]
User=omarchytest
Session=omarchy.desktop
```

`CompositorCommand` configures the compositor used by the SDDM greeter. It
does **not** make each user session start Hyprland. The current automatic
selection is specifically `Session=omarchy.desktop`; SDDM also remembers the
last selected session.

### Installed Hyprland session entries

`/usr/local/share/wayland-sessions/omarchy.desktop` is the Omarchy entry:

```ini
[Desktop Entry]
Name=Omarchy (Hyprland uwsm)
Comment=Omarchy Hyprland session
Exec=uwsm start -g -1 -e -D Hyprland hyprland.desktop
TryExec=uwsm
Type=Application
```

The packaged plain Hyprland entry is
`/usr/share/wayland-sessions/hyprland.desktop`, which uses
`Exec=/usr/bin/start-hyprland`. The UWSM-managed alternative is
`/usr/share/wayland-sessions/hyprland-uwsm.desktop`:

```ini
[Desktop Entry]
Name=Hyprland (uwsm-managed)
Comment=An intelligent dynamic tiling Wayland compositor
Exec=uwsm start -e -D Hyprland hyprland.desktop
TryExec=uwsm
Type=Application
DesktopNames=Hyprland
```

The Omarchy entry adds `-g -1`; it is intentionally the session entry to
preserve and select when returning to Omarchy.

### UWSM and the graphical user session

`graphical-session.target` is active. UWSM creates a Hyprland-specific user
session tree, including active
`wayland-session@Hyprland.desktop.target`,
`wayland-session-pre@Hyprland.desktop.target`,
`wayland-session-xdg-autostart@Hyprland.desktop.target`, and
`wayland-session-envelope@Hyprland.desktop.service` units. The discovered
`wayland-wm@Hyprland.desktop.service` unit was inactive after its launch
handoff, while the session targets remained active.

Observed user-manager environment relevant to desktop startup includes:

- `DESKTOP_SESSION=omarchy`
- `DISPLAY=:0`
- `XDG_RUNTIME_DIR=/run/user/1000`
- `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus`
- `GDK_BACKEND=wayland,x11,*`
- `ELECTRON_OZONE_PLATFORM_HINT=wayland`
- Fcitx input-method variables (`INPUT_METHOD`, `QT_IM_MODULE`,
  `XMODIFIERS`, and `SDL_IM_MODULE`)

Omarchy-related user units currently present include
`omarchy-crash-watch.service`, `omarchy-fcitx5.service`,
`omarchy-migrate-notify.service`, `omarchy-server-internal-monitor.service`,
and `omarchy-sleep-lock.service`. The crash watcher is explicitly attached
to `graphical-session.target` (`After=`, `PartOf=`, and `WantedBy=`) and is
gated on `ConditionEnvironment=WAYLAND_DISPLAY`; it is Wayland-session-aware
rather than a reason to force Plasma through Hyprland. The active graphical
session also starts `xdg-desktop-portal-hyprland.service`, which is a
Hyprland-specific portal implementation and a primary coexistence risk.

### Plasma registration and recommended method

Plasma should be installed through its normal Arch packages and allowed to
provide its own Wayland session `.desktop` file under
`/usr/share/wayland-sessions/`. SDDM discovers entries in its session
directories automatically; it can therefore present both the existing
`omarchy.desktop` entry and Plasma's packaged session without replacing
Hyprland or SDDM.

The exact Plasma session filename and `Exec=` value must be discovered from
the installed package rather than hard-coded by the future switcher. The
baseline's local pacman file database did not contain `plasma-workspace`, so
its file list could not be inspected before installation. The switcher should
enumerate installed Wayland session entries and identify the one supplied by
the Plasma package after installation.

**Proposed smallest supported change set, not yet performed:**

1. Install the Plasma Wayland packages only; leave `sddm`, Hyprland, UWSM,
   Omarchy session files, and the SDDM greeter compositor unchanged.
2. Verify the packaged Plasma Wayland `.desktop` entry and its direct
   `Exec=` command after the package transaction.
3. Let SDDM launch that packaged Plasma session directly. Do not run Plasma
   through `uwsm start` and do not create a custom user systemd service.
4. Keep `/usr/local/share/wayland-sessions/omarchy.desktop` unchanged.
5. For an interactive session chooser, add a later, reversible SDDM override
   that disables autologin; alternatively a switcher can set SDDM's
   `Autologin/Session` to the validated session-entry filename. Do not edit
   the existing Omarchy file in place.
6. Test a Plasma login, then an SDDM return to `omarchy.desktop`, on the
   current writable overlay before designing any user-facing automation.

### Risks to test after installation

- SDDM currently autologins `omarchy.desktop`; users will not be offered a
  choice at boot until autologin is disabled or its configured session is
  changed.
- Plasma has its own Wayland/systemd user-session lifecycle. Wrapping it in
  UWSM or an extra custom systemd service would duplicate session ownership,
  bypass SDDM selection semantics, and risk competing lifecycle/seat state.
- `xdg-desktop-portal-hyprland` and Hyprland-oriented Omarchy user services
  must not be left as the chosen portal/session implementation under Plasma.
  The post-install test must inspect the Plasma portal and user-unit set.
- Omarchy environment defaults and input-method variables can be inherited by
  a different session; verify that they do not override Plasma's intended
  behavior.

No package, service, SDDM configuration, session entry, host configuration,
baseline QCOW2 image, or live-overlay repair was changed during this
investigation.

## 2026-09-23 — Dual desktop login and desktop-manager integration

All changes in this section were made in the active
`omarchy-kde-after-baseline.qcow2` overlay. The preserved
`omarchy-kde.qcow2` baseline was not modified.

### Installed sessions and SDDM

Plasma was already installed when this phase resumed:

- `plasma-meta 6.7-2`
- `plasma-workspace 6.7.4-3`
- `breeze 6.7.4-2`
- `sddm 0.21.0-7`

The two supported entries are:

| Desktop | Session file | Launch path |
| --- | --- | --- |
| Omarchy | `/usr/local/share/wayland-sessions/omarchy.desktop` | `uwsm start -g -1 -e -D Hyprland hyprland.desktop` |
| KDE Plasma | `/usr/share/wayland-sessions/plasma.desktop` | `/usr/lib/plasma-dbus-run-session-if-needed /usr/bin/startplasma-wayland` |

The original Omarchy session file and original SDDM fragments were retained.
The SDDM configuration was backed up in
`/var/lib/omarchy-desktop-manager/backups/pre-breeze-20260923/`.

Breeze first proved that SDDM could visibly offer both sessions. An independent
Breeze-derived theme was then installed at
`/usr/share/sddm/themes/omarchy-desktop-manager`. The final override is
`/etc/sddm.conf.d/zzzz-omarchy-desktop-manager.conf`; it selects that theme,
keeps `RememberLastUser=true` and `RememberLastSession=true`, and disables
autologin. The original `/usr/share/sddm/themes/omarchy` and installed Breeze
theme remain available as fallbacks.

The custom greeter visibly provides:

- Omarchy and Plasma session selection
- password login
- an AccountsService avatar
- a replaceable wallpaper
- Breeze-derived reboot and shutdown controls

Wallpaper and avatar installation were verified through the validated helpers
`/usr/local/bin/omarchy-desktop-theme` and
`/usr/local/libexec/omarchy-desktop-manager-theme`. The reboot and power-off
buttons retain Breeze's `sddm.reboot()` and `sddm.powerOff()` implementation;
they were inspected but not deliberately activated during the final pass.

### Verified desktop launches

Both entries were launched through SDDM and tested as real graphical sessions:

- Plasma reported a Wayland session owned by SDDM and ran
  `startplasma-wayland`, `kwin_wayland`, and `plasmashell`.
- Omarchy ran Hyprland, UWSM, Quickshell, and the preserved Omarchy session
  entry.
- Plasma used `plasma-xdg-desktop-portal-kde.service`; the Hyprland portal was
  inactive.
- Omarchy used `xdg-desktop-portal-hyprland.service`; Plasma targets and the KDE
  portal were inactive.
- Guest network connectivity succeeded in both sessions.
- Native logout was verified with `org.kde.Shutdown` in Plasma and `uwsm stop`
  in Omarchy.
- Clean Omarchy -> Plasma -> Omarchy and Plasma -> Omarchy -> Plasma cycles
  succeeded.

Restarting SDDM over a still-running Plasma session once left Plasma targets in
the persistent user manager. UWSM correctly refused to start a second
graphical session with “A compositor or graphical-session* target is already
active!” Native desktop logout and a clean reboot did not reproduce this
artificial failure; SDDM must not be restarted over an active desktop as a
session-switch test.

### Default Desktop integration

The supported user extension
`~/.config/omarchy/extensions/omarchy-menu.jsonc` now adds
`Setup > Defaults > Desktop`. Packaged files under `/usr/share/omarchy` were
not edited. The previous user extension is retained as
`omarchy-menu.jsonc.pre-desktop-manager`.

`/usr/local/bin/omarchy-default-desktop` discovers and validates only the
supported `omarchy.desktop` and `plasma.desktop` entries. It displays the
configured default, changes it through Polkit, and optionally offers a
confirmed immediate logout using the active desktop's native logout path.
The chooser was corrected to avoid whitespace-sensitive `gum` labels.

The privileged helper
`/usr/local/libexec/omarchy-desktop-manager-set-default` stores the independent
preference in `/var/lib/omarchy-desktop-manager/default-session` and updates
SDDM state atomically. The enabled
`omarchy-desktop-manager-default.path` watches `/var/lib/sddm/state.conf`, and
`omarchy-desktop-manager-default.service` restores the configured preference
after a one-time SDDM selection.

Verified behavior:

- Declining “switch now” changed the future default but left Plasma running.
- Accepting it used Plasma's native logout, returned to SDDM, and launched
  Omarchy successfully.
- A one-time Plasma selection launched Plasma while the configured Omarchy
  default remained unchanged.
- The reciprocal test launched Omarchy once while Plasma remained the default;
  after native Omarchy logout, SDDM visibly selected Plasma again.
- The path unit remained active and its no-op synchronization did not loop.

## 2026-09-23 — Frankenstein Omarchy Shell profile for KDE Plasma

### Why the stock shell is not launched wholesale

The stock Omarchy shell is a single Quickshell process containing the bar,
menus, notifications, lock/idle integration, Polkit agent, overlays, and
plugins. Hyprland starts it from
`/usr/share/omarchy/default/hypr/autostart.lua` through
`omarchy-launch-shell`; the stock restart helper dispatches through `hyprctl`.

A live stock-shell probe under Plasma rendered, but was rejected as the final
design because it:

- overlaid an Omarchy top bar on Plasma's panel
- attempted to claim `org.freedesktop.Notifications`
- attempted to register a second Polkit agent
- started Omarchy idle/lock handling
- loaded Hyprland workspace and monitor assumptions

The probe was stopped. It demonstrated that the menu itself works under KWin,
but that a full unfiltered shell would create two competing desktop shells.

### Desktop-specific profile architecture

The KDE adapter uses a filtered copy of the Omarchy shell host while loading
the installed first-party plugins from `/usr/share/omarchy/shell/plugins`.
Packaged Omarchy sources remain read-only.

Installed files:

| File | Purpose |
| --- | --- |
| `/etc/frankenstein/shell-profiles/plasma.json` | Declarative KDE profile and native/unsupported feature list |
| `/usr/local/share/frankenstein/omarchy-shell/shell.qml` | Profile-aware shell host; suppresses the Omarchy bar |
| `/usr/local/share/frankenstein/omarchy-shell/services/PluginRegistry.qml` | Enforces the profile plugin allowlist |
| `/usr/local/bin/frankenstein-shell-adapter` | Desktop detection, launch, IPC, native settings adapters, enable/disable, and compatibility checks |
| `~/.config/systemd/user/frankenstein-omarchy-shell.service` | Owns the filtered Quickshell process and follows the Plasma session |
| `~/.config/autostart/frankenstein-omarchy-shell.desktop` | KDE-only automatic startup on every Plasma login |
| `~/.local/share/applications/frankenstein-omarchy-menu.desktop` | Exposes “Omarchy Setup Menu” through Plasma's native application launcher |

The wrapper shell symlinks its `Commons`, `Ui`, `plugins`, and unchanged service
sources to the installed Omarchy tree. Its copied host and registry are the
desktop-compatibility boundary. This leaves the original Hyprland shell
unchanged and provides an explicit place for future GNOME or other profile
allowlists and adapters.

The Plasma profile permits only `omarchy.menu`. It does not instantiate an
Omarchy bar or any other first-party plugin. Plasma remains the native owner of:

- panel and application launcher
- wallpaper
- lock screen and idle management
- notifications
- Polkit authentication agent
- workspaces
- OSD

The shared Omarchy menu extension adds desktop-aware adapters:

- Displays -> KDE Display Configuration under Plasma; Hyprland monitor config
  under Omarchy
- Keybindings -> KDE shortcut settings under Plasma; Hyprland bindings under
  Omarchy
- Input -> KDE input settings under Plasma; Hyprland input config under
  Omarchy
- Choose or Switch Now -> a native terminal launch under Plasma and the stock
  Omarchy floating-terminal path under Hyprland

Hyprland-only plugin/config entries are hidden under Plasma instead of being
deleted. The profile also provides an Omarchy Shell Integration submenu with a
compatibility check and a disable action.

### KDE feature verification

Verified under a real Plasma Wayland login:

| Feature | Result |
| --- | --- |
| Filtered shell startup | Pass: exactly one `/usr/local/share/frankenstein/omarchy-shell` Quickshell process |
| Effective plugin set | Pass: only `omarchy.menu` |
| Omarchy bar | Disabled; no panel overlap |
| Omarchy Setup menu | Pass from IPC and Plasma's application entry |
| Default Desktop submenu | Pass; Omarchy, KDE Plasma, and confirmed switch action visible |
| Plasma terminal adapter | Pass: opened the configured terminal without `uwsm-app` |
| KDE display adapter | Pass: opened Plasma Display Configuration |
| Plasma panel/wallpaper/workspaces | Preserved |
| Plasma notification owner | Preserved; no second notification-server warning |
| Plasma Polkit agent | Preserved; exactly one agent process |
| Plasma lock/idle | Preserved; the native Plasma lock screen activated |
| KDE portal | Active; Hyprland portal inactive |
| Subsequent Plasma login | Pass: KDE autostart recreated the filtered service |
| Disable/re-enable | Pass: disable stopped the adapter process while Plasma stayed active; enable restored it |
| Return to Omarchy | Pass: adapter inactive, no custom shell, exactly one stock Omarchy shell, stock IPC `ok` |
| Return to Plasma | Pass: no stock shell, one filtered shell, menu IPC `ok` |

The VM still emits benign virtio/Mesa EGL warnings. One standalone
`kcmshell6 kcm_kscreen` probe produced a KDE crash notification, while the
actual `systemsettings kcm_kscreen` adapter opened Display Configuration.
Plasma also retains its existing Fcitx Wayland diagnostic. These do not justify
claiming broader compatibility.

### Explicitly unsupported or not yet adapted under Plasma

- Omarchy bar and its Hyprland workspace widget
- Omarchy lock and idle services
- Omarchy notifications and Polkit agent
- Omarchy wallpaper/background service
- Omarchy OSD
- Hyprland monitor controls
- Hyprland screenshot/screen-record actions
- non-menu Omarchy overlays, panels, and third-party shell plugins

These components remain installed and fully available in the Omarchy/Hyprland
session. They are filtered only while the Plasma profile is active. GNOME and
other desktop profiles have not been implemented or tested.

### Compatibility checks

Run inside Plasma:

```bash
frankenstein-shell-adapter check
```

A passing result requires the KDE desktop, enabled integration, active service,
one adapter shell process, working IPC, and exactly `omarchy.menu` as the
effective plugin set. It also reports the native component policy,
notification owner, and Polkit-agent count.

To disable or re-enable the additional integration without removing Plasma:

```bash
frankenstein-shell-adapter disable
frankenstein-shell-adapter enable
```

### Rollback

To remove only Frankenstein's Plasma shell adapter:

```bash
systemctl --user stop frankenstein-omarchy-shell.service
rm -f ~/.config/autostart/frankenstein-omarchy-shell.desktop
rm -f ~/.config/systemd/user/frankenstein-omarchy-shell.service
rm -f ~/.local/share/applications/frankenstein-omarchy-menu.desktop
sudo rm -f /usr/local/bin/frankenstein-shell-adapter
sudo rm -rf /usr/local/share/frankenstein/omarchy-shell
sudo rm -f /etc/frankenstein/shell-profiles/plasma.json
systemctl --user daemon-reload
```

Restore the pre-manager Omarchy menu extension:

```bash
cp ~/.config/omarchy/extensions/omarchy-menu.jsonc.pre-desktop-manager \
  ~/.config/omarchy/extensions/omarchy-menu.jsonc
```

To remove the Default Desktop synchronization:

```bash
sudo systemctl disable --now omarchy-desktop-manager-default.path
sudo rm -f /etc/systemd/system/omarchy-desktop-manager-default.path
sudo rm -f /etc/systemd/system/omarchy-desktop-manager-default.service
sudo rm -f /usr/local/bin/omarchy-default-desktop
sudo rm -f /usr/local/libexec/omarchy-desktop-manager-set-default
sudo rm -rf /var/lib/omarchy-desktop-manager
sudo systemctl daemon-reload
```

To return SDDM to the original Omarchy configuration, remove the late override
and restart SDDM only from a logged-out state or after reboot:

```bash
sudo rm -f /etc/sddm.conf.d/zzzz-omarchy-desktop-manager.conf
sudo systemctl restart sddm
```

The custom theme and helpers can then be removed independently:

```bash
sudo rm -rf /usr/share/sddm/themes/omarchy-desktop-manager
sudo rm -f /usr/local/bin/omarchy-desktop-theme
sudo rm -f /usr/local/libexec/omarchy-desktop-manager-theme
```

### Temporary-access cleanup

After final verification:

- the ephemeral public key was removed from the guest's `authorized_keys`
- the UFW rule allowing TCP port 22 only from `10.0.2.2` was removed
- `sshd.service` was disabled and stopped
- the dynamic QEMU forward from `127.0.0.1:2222` to guest port 22 was removed
- the ephemeral private/public keys and temporary known-hosts file were deleted
  from session-state storage

The unrelated localhost port-8000 QEMU forward was left unchanged. The
canonical `start-vm.sh` contains no SSH forwarding rule.
