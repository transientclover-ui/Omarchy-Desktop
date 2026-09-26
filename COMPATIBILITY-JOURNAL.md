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

## 2026-09-23: first-run package checkpoint (paused)

### Package layout

An uncommitted split-package implementation was completed and preserved for
continued testing:

- `frankenstein-core` owns the `frankenstein` CLI, setup and rollback logic,
  default-desktop helper, privileged writer, systemd path/service units,
  documentation, and licenses.
- `frankenstein-kde` depends on the exact matching core package and owns the
  Plasma adapter, profile, menu overlay, filtered Omarchy Shell files, user
  unit/autostart/application templates, and the reversible Breeze SDDM
  configuration template.
- Pacman-owned files use `/usr/bin`, `/usr/lib/frankenstein`, and
  `/usr/share/frankenstein`; no package owns `/usr/local`.
- Package installation is inert. It neither enables services nor writes user
  configuration; the user must explicitly run `frankenstein setup`.
- All experimental files under `src/sddm/` are excluded from both packages.
  The packaged SDDM override is an original MIT-licensed configuration file at
  `src/frankenstein/zzzz-frankenstein.conf`; it selects installed Breeze and
  disables autologin without bundling theme code or artwork.

The packages were built twice with a fixed `SOURCE_DATE_EPOCH` before the final
installer correction and produced identical SHA-256 hashes. After correcting
the installer, source checks passed and both packages rebuilt successfully.
A second reproducibility comparison of that corrected build remains pending.

### Fresh baseline-overlay evidence

Test VM files:

- preserved baseline: `omarchy-kde.qcow2`
- writable test overlay: `omarchy-frankenstein-installer-test.qcow2`
- read-only package disk: `frankenstein-installer-payload.img`
- writable evidence disk: `frankenstein-installer-results.img`
- dedicated launcher: `start-installer-test-vm.sh`

The test overlay is backed directly by `omarchy-kde.qcow2`. QEMU was stopped
through QMP after it did not respond to an ACPI power-down request. There were
no active block jobs, `qemu-img check` subsequently reported no errors, and
the baseline SHA-256 matched the value recorded before boot. No VM process or
control socket remained active at the pause point.

Observed results:

| Test | Result |
|---|---|
| Initial local package transaction | Expected failure: untouched baseline had no downloaded pacman databases |
| Guest repository database refresh | Pass; core, extra, multilib, and Omarchy databases synchronized |
| Split-package installation | Pass; Plasma dependencies plus `frankenstein-core` and `frankenstein-kde` installed |
| Read-only packaged preflight | Pass; detected Omarchy 4.0.4-1, valid Omarchy and Plasma sessions, original SDDM theme, and pacman-owned payload |
| Failure rollback | Pass for the observed backup-checksum failure; setup removed partial state and a second preflight was permitted |
| Corrected first-run setup | Pass; backups created, Breeze override installed, default path unit enabled, and Omarchy remained the default |
| Original Omarchy session after setup | Pass; Hyprland remained graphical and exactly one stock `/usr/share/omarchy/shell` process was present |
| Breeze session list visibility | Pass; Omarchy, two Hyprland variants, and Plasma (Wayland) were visible |
| Breeze session selection | Unresolved; wheel input highlighted Plasma, but click, Enter, and physical keyboard selection did not activate the highlighted entry |
| Plasma session launch | Partial; setting `plasma.desktop` through the validated helper updated SDDM and authentication entered Plasma |
| Plasma graphical readiness | Fail; the fresh-overlay Plasma session remained black, so Plasma is not yet verified |
| Upgrade, downgrade, package removal | Not run |

The first setup attempt exposed incorrect literal quoting in the system-backup
checksum loop. Its failure trap ran, then the command was corrected and the
packages were rebuilt. The corrected setup completed successfully. Evidence
logs are retained on the results disk as `package-install*.log`,
`preflight.log`, `setup.log`, `setup-fixed.log`,
`omarchy-after-setup.log`, `session-attempts.log`, and
`default-switch.log`.

### Resume procedure

1. Boot the preserved test overlay:

   ```bash
   ./start-installer-test-vm.sh
   ```

2. Unlock the encrypted VM disk directly in the QEMU window. SDDM now defaults
   to Plasma because the final test set `plasma.desktop`.
3. Reproduce the black screen, switch to a text console, and capture at least:

   ```bash
   systemctl --user --failed
   systemctl --user status plasma-workspace.target frankenstein-omarchy-shell.service
   journalctl --user -b --no-pager
   journalctl -b -u sddm --no-pager
   pgrep -af 'plasmashell|kwin_wayland|quickshell'
   ```

4. Mount the evidence disk at `/mnt/fr` and save diagnostics there. Determine
   whether Plasma itself, the KDE autostart template, or the filtered shell is
   responsible before changing code.
5. Retest SDDM selector activation independently. A visible Plasma entry alone
   does not satisfy the selector requirement.
6. After fixing the root cause, verify Plasma, native logout back to SDDM,
   Omarchy return, package upgrade, downgrade, `frankenstein uninstall`, and
   package removal.
7. Rebuild the corrected packages twice and compare their unsigned hashes.

No host desktop configuration, host SDDM configuration, host package database,
or host installed package was changed during this test.

## 2026-09-23: fresh-overlay package lifecycle completed

Testing resumed from checkpoint `1c5ccaa`. Before boot, exact project-local
copies of the writable test overlay, installer-test UEFI variables, and results
disk were saved under `checkpoints/`. The baseline image remained unchanged and
the writable overlay passed an offline `qemu-img check`.

### Plasma black-screen root cause and fix

The black screen was reproduced after a successful SDDM authentication. KWin
was running and owned the rendered cursor, but `plasma-plasmashell.service`
failed three times with:

```text
starting invalid corona "org.kde.plasma.desktop"
```

The guest had `plasma-workspace` but not `plasma-desktop`; consequently
`/usr/share/plasma/shells/org.kde.plasma.desktop` did not exist. The
`frankenstein-kde` package dependency was corrected to include
`plasma-desktop`.

An independent adapter error also caused
`frankenstein-omarchy-shell.service` to restart continuously:

```text
Failed to load configuration
caused by @shell.qml[239:5]: Bar is not a type
```

The filtered shell disables the bar at runtime, but QML still resolves the
statically imported `Bar` type. The package now supplies an inert symlink from
its shell tree to `/usr/share/omarchy/shell/plugins/bar`. The profile still
sets `FRANKENSTEIN_SHELL_NO_BAR=1`, so Plasma remains the only panel owner.

Both corrections are in package revision `0.1.0-2`. After installing that
revision, `plasma-plasmashell.service` and
`frankenstein-omarchy-shell.service` became active with no failed user units.
The desktop rendered with Plasma's native panel and wallpaper. The KDE portal
was active, the Hyprland portal was inactive, Plasma owned notifications, and
`frankenstein-shell-adapter check` reported one filtered shell with only
`omarchy.menu` enabled.

### Breeze session selector

The stock Breeze selector was retested independently. A normal pointer press
and release opened the menu, selecting `Omarchy (Hyprland uwsm)` updated the
footer immediately, and password authentication launched the selected Omarchy
session. The earlier highlight-only observation was caused by test input
timing, not a Breeze activation defect.

Native Plasma logout returned to Breeze. Omarchy then launched through its
preserved UWSM entry with one stock Omarchy shell, the Hyprland portal active,
the KDE portal inactive, the Frankenstein adapter inactive, and no failed
user units.

### Package lifecycle results

| Test | Result |
|---|---|
| Upgrade `0.1.0-1` to `0.1.0-2` | Pass; `plasma-desktop` was installed and both graphical services recovered |
| Downgrade `0.1.0-2` to `0.1.0-1` | Pass; Omarchy remained active |
| Re-upgrade to `0.1.0-2` | Pass; corrected payload and bar symlink restored |
| `frankenstein uninstall --yes` | Pass; user integration, SDDM override, default-session state, and enabled path unit were removed |
| Remove both Frankenstein packages | Pass; package-owned payload disappeared while Plasma packages and the active desktop remained intact |
| Omarchy after rollback | Pass; one stock `/usr/share/omarchy/shell` process and no failed user units |
| Plasma after package removal | Pass; native Plasma shell and KDE portal remained active without Frankenstein |
| Reproducible revision-2 build | Pass; two clean builds produced identical unsigned SHA-256 hashes |

Unsigned revision-2 package hashes:

```text
152caacb8c4849e0a364e33d21cc2a6382828a9c98b8c38a0e0c9440e0c8a90b  frankenstein-core-0.1.0-2-x86_64.pkg.tar.zst
7c372a0d749b7ef061fd0353c5b9e713081e597294ed344cebb6d0fec20dde2e  frankenstein-kde-0.1.0-2-x86_64.pkg.tar.zst
```

Diagnostics, screenshots, package hashes, and reproducibility manifests are
retained under `evidence/checkpoint-20260923-fresh-overlay/`. No package
signing or trust configuration was added.

The final guest state has both Frankenstein packages removed and the original
Omarchy SDDM configuration restored. Plasma remains installed because
dependency removal is intentionally an explicit administrator decision.

The temporary SSH key and narrow UFW rule were removed, `sshd` was returned to
its disabled state, and the runtime-only QEMU forwarding disappeared at
shutdown. A final reboot required only the encrypted-disk unlock; the restored
Omarchy configuration then autologged into a working Hyprland desktop without
an SDDM password prompt.

The guest was shut down through Omarchy's native power menu. The final overlay
passed offline `qemu-img check`, the preserved baseline still hashed to
`844be5c310a5750902c40d1ab95fb5144b6788b29cbfa7d3b96b29aaa253c4c0`,
and the evidence directory was verified directly on the unmounted results
image. Final recovery copies are:

```text
88cf4233da8d265a926d836dff51b841101055e082e189eb6fab0b102f739308  checkpoints/omarchy-frankenstein-final-20260923.qcow2
7bcf10d11d8617b663214bfbf0c0180f3c4d72b8342999573aa684cb5dc25cc8  checkpoints/OVMF_VARS-frankenstein-final-20260923.fd
713b6e2108fbd2e463a4e3699543210bd2b7dfda4799ed602cd74a3e400fd6f6  checkpoints/frankenstein-results-final-20260923.img
```

No VM process or control socket remained active. No host desktop
configuration, host SDDM configuration, host package database, host installed
package, package-signing configuration, or trust configuration was changed.

## 2026-09-23: signed repository workflow completed

Package revision `0.1.0-2` was frozen as the compatibility release-candidate
baseline. A disposable VM-only Ed25519 OpenPGP key was then created in the
Git-ignored `.signing/test-repository/` keyring. Its full fingerprint was:

```text
506AE0340CB7DAF54767BB25F205C2BA26C570ED
```

The private key never left that isolated project directory. Only the armored
public key and full fingerprint were copied into the test repository. No key
was imported into the development host's pacman keyring.

Signed install and update snapshots contained detached package signatures,
signed `frankenstein.db` and `frankenstein.files` databases, the public key,
fingerprint, and a SHA-256 manifest. Local verification of every package and
database signature passed.

### Clean baseline-backed install

A new writable overlay backed directly by the immutable clean Omarchy image
was booted with a read-only repository disk and a separate writable results
disk. The guest initially contained no Frankenstein package or repository
configuration.

The public key's complete fingerprint was verified before it was added to the
VM pacman keyring and locally signed. The VM-only repository used:

```ini
SigLevel = Required DatabaseRequired
```

Pacman synchronized the signed database and installed signed
`frankenstein-core 0.1.0-2` and `frankenstein-kde 0.1.0-2`.
`frankenstein preflight` and `frankenstein setup --yes` passed. Omarchy
remained healthy, and an explicit Breeze selection launched Plasma with its
native panel, KDE portal, notification service, and Polkit agent plus one
filtered Frankenstein shell.

### Signed update

Omarchy's direct-pacman guard correctly rejected an ordinary `pacman -Syu`.
The documented normal-system path is `omarchy update`; only this controlled VM
test used Omarchy's explicit `OMARCHY_ALLOW_DIRECT_PACMAN=1` override.

An initial update candidate reused revision `0.1.0-3` after its package bytes
had changed. Pacman correctly rejected the cached package/signature mismatch.
No cache or integrity bypass was used. Revision `0.1.0-3` is abandoned and
must not be published.

The local-source build helpers were corrected to remove stale makepkg
`file://` source copies before checksum generation and package builds. The
replacement `0.1.0-4` packages were built twice with identical unsigned
hashes:

```text
3eaca0497d108afe5666d9f848cb76af7d1d7943393c8b19224563497e3ce07f  frankenstein-core-0.1.0-4-x86_64.pkg.tar.zst
3f507ab506c9a03645cb156cb17062c8a864eb9e7010d6092ef75b00b178f628  frankenstein-kde-0.1.0-4-x86_64.pkg.tar.zst
```

After publishing only that signed snapshot to the VM-local repository,
`pacman -Syu` upgraded both packages from `0.1.0-2` to `0.1.0-4`. Updated
Omarchy passed with its stock shell and Hyprland portal. Updated Plasma passed
after an explicit post-restart Breeze selection, with:

- `Desktop=KDE`, `Type=wayland`, and an active login session
- active `plasma-plasmashell.service`
- running KDE portal backend and inactive Hyprland portal
- one filtered shell with only `omarchy.menu` enabled
- native Plasma panel, notifications, Polkit agent, wallpaper, lock screen,
  idle management, workspaces, and OSD
- no failed user units

An intermediate login launched Omarchy because the intended selector choice
had not been explicitly activated after restarting SDDM. Reopening the
selector and clicking `Plasma (Wayland)` launched Plasma correctly; this
matched the earlier press-and-release selector finding rather than exposing a
new session defect.

### Cleanup and recovery

The VM-only repository configuration, copied repository, and pacman trust were
removed. The temporary SSH key and narrow UFW rule were deleted, and `sshd`
was disabled before a native Plasma shutdown. The overlay passed offline
`qemu-img check`, the results filesystem passed read-only `e2fsck`, and the
baseline still hashed to:

```text
844be5c310a5750902c40d1ab95fb5144b6788b29cbfa7d3b96b29aaa253c4c0  omarchy-kde.qcow2
```

Install, update, version, cleanup, and post-update Plasma evidence is retained
under `evidence/repository-workflow-20260923/`. Final recovery copies are:

```text
60a931b54e403842d5c50c67ea7727ee8b090cbcb15f6133a7bd615da5b2244a  checkpoints/omarchy-repository-test-final-20260923.qcow2
4c1d2ecdbf348ed1556c5a996a36e869e15cf667d93f4edd34786c878e73434f  checkpoints/OVMF_VARS-repository-test-final-20260923.fd
59030537581c1103e81709b67208cc7f683f22e67bb8b4cbf149c7d6920d54c6  checkpoints/frankenstein-repository-results-final-20260923.img
```

No VM process or control socket remained active. The repository was not
published, and no host package, desktop, pacman configuration, signing-key
trust, or Frankenstein installation was changed.

## 2026-09-23: paused SDDM rollback and configurable-shell work

Work was paused by explicit user request with a partial, unvalidated
implementation in the tree. No corrected package was built or installed, and
no disposable-VM validation was started.

The checkpoint currently contains:

- an initial helper for backing up and restoring `/var/lib/sddm/state.conf`
  across existing-file, absent-file, failed-setup, and uninstall paths
- initial `auto` default-session logic that prefers the active supported
  desktop, allowing an existing Plasma session to remain the default
- backup-only coverage for `kwinoutputconfig.json`, `ksmserverrc`,
  `powermanagementprofilesrc`, and `Trolltech.conf`
- initial shell-profile override support under
  `~/.config/frankenstein/plasma.json`, separate from the stock Omarchy
  `shell.json`
- initial regression scripts for installer state and shell-profile merging
- initial PKGBUILD source/install entries for the new helpers

This state is not release-ready. A regression-test command was interrupted
before completion, and the partial implementation has not received a complete
review. Package checksums, `.SRCINFO`, and `pkgrel` have not been updated.

Resume from this checkpoint by:

1. Review the partial installer-state and shell-profile implementation for
   syntax, rollback ordering, missing variables, and package/standalone parity.
2. Complete the read-only classification of currently enabled Omarchy Shell
   components and user plugins for Plasma.
3. Run and fix the regression tests, then add any missing setup-failure and
   uninstall integration cases.
4. Update documentation, package checksums, `.SRCINFO`, and assign a new
   package revision without reusing prior package bytes.
5. Rebuild reproducibly and validate the corrected packages only in a fresh
   disposable baseline-backed VM, including SDDM state restoration and
   configurable non-menu profiles.
6. Return to the real host only for a new read-only preflight and installation
   plan after VM validation passes.

The real host remained unchanged: Frankenstein was not installed, no package
or repository trust was added, and no SDDM configuration or service state was
modified.

## 2026-09-23: shell-profile regression suite repaired

Resumed from `a14c43c` (`Checkpoint partial host adoption fixes`). The tracked
working tree was clean; the existing untracked `iso-readme.md`,
`omarchy-4.0.4.iso.sha256`, and `upstream-boot.sh` were left untouched.

The single task in this continuation was to complete the local shell-profile
merge regression suite from resume item 3. The checkpoint's suite failed on
its first plugin-list assertion because a single-quoted jq expression included
literal backslashes before its string delimiters. Both affected expressions
were corrected. No production implementation was changed.

Coverage now checks absent overrides, panel-only and plugin-only overrides,
replacement of plugin arrays (including an empty array), preservation of all
other packaged fields, and unchanged source files. Twenty-two independent
invalid-override cases exercise malformed JSON, schema/type errors, forbidden
fields, invalid panels, invalid plugin identifiers, and duplicate identifiers.
Each is rejected by both the validator and the merge entry point without
emitting an effective profile. An invalid packaged profile is also rejected
even when an override could replace its invalid field.

Validation:

- `bash tests/shell-profile.sh`: passed, including all 22 rejection cases.
- `bash tests/installer-state.sh`: passed the existing helper-level cases.
- Bash syntax checks for both suites and `src/lib/shell-profile.sh`: passed.
- `git diff --check`: passed.

These are local helper tests only. They do not validate QML loading, non-menu
plugin compatibility, adapter startup, setup-failure/uninstall integration, or
SDDM rollback in a real session. The remaining review, component classification,
integration cases, package metadata/revision updates, reproducible builds, and
fresh disposable-VM validation recorded above remain pending. No package was
built or installed, no VM was started, and no host desktop, service, package,
or trust configuration was changed.

## 2026-09-23: isolated SDDM rollback integration tests

Completed the next bounded task: exercise the actual packaged-layout installer
and uninstaller control flow for failed setup and uninstall, using temporary
filesystem fixtures and simulated system services. The new test is run with:

```bash
python3 tests/installer-rollback.py
```

It requires Linux user namespaces, bubblewrap, Python 3, Bash, and jq. It fails
closed if sandboxing is unavailable. Host files are mounted read-only, fixture
paths are writable only inside the temporary tree, networking is isolated, and
package/service/default-writer commands are simulated. The real installer,
uninstaller, and SDDM backup/restore helper execute without source rewriting.

The initial test reproduced restoration while a simulated synchronization
service remained active. Disabling the path watcher alone does not stop the
independent oneshot service it previously activated. Both rollback paths now
stop the watcher first and then stop/wait for the service before restoring
SDDM state. If either stop fails, they report incomplete cleanup and preserve
recovery data instead of attempting restoration; uninstall also retains its
active installation record for retry.

Validation passed:

- Four integration cases: failed setup after SDDM mutation and successful
  setup followed by uninstall, each with existing and initially absent state.
- Existing state restored with exact bytes, mode, uid/gid, and nanosecond mtime;
  initially absent state removed; original SDDM configuration and backups
  preserved; successful cleanup removes the override and active record.
- Four additional cases inject watcher/service stop failures in each rollback
  path and verify diagnostics, unchanged mutated state, and recovery retention.
- Existing installer-state and shell-profile regression suites.
- Bash syntax checks for changed scripts and the installer-state helper, plus
  `git diff --check`.

This validates packaged-layout control flow with simulated services, not real
systemd timing, SDDM sessions, standalone-install parity, or every setup failure
point. No VM or real service was started, and no package was built or installed.
Package checksums, revision, and `.SRCINFO` remain pending alongside the broader
partial-work review and disposable-VM validation. These tests do not make the
checkpoint release-ready.

## 2026-09-23: checkpoint after local rollback validation

Checkpoint requested after the shell-profile regression repair and isolated
SDDM rollback tests above. These changes are saved together; the three unrelated
untracked ISO/boot reference files remain outside the checkpoint.

Next small task: inject a failure in SDDM state restoration itself. The current
setup rollback prints a restoration error but continues removing state and
ultimately claims completed mutations were rolled back. Verify failure behavior
in both setup rollback and uninstall, preserve recovery information, and make
incomplete-cleanup reporting accurate. This task has not yet been implemented.

Resume by reading this journal and inspecting the working tree. Continue with
one bounded task; do not treat local regression passes as package, real-systemd,
or VM validation. Package metadata/checksum/revision updates, broader partial
implementation review, reproducible builds, and disposable-VM validation remain
pending. No host installation is authorized by this checkpoint.

## 2026-09-23: KDE-only continuation — restoration failures

Resumed from `0cfd79f` with the public-project naming checkpoint kept separate.
Current scope is a KDE proof of concept; other desktops and broader plugin
support are not prerequisites for this milestone. The three pre-existing
untracked ISO/boot reference files were left untouched.

The isolated packaged-layout test reproduced setup rollback reporting success
and removing recovery-related state after SDDM restoration failed. Setup now
stops that cleanup, preserves recovery data, reports incomplete rollback with
its backup location, and retains the original setup failure exit status.
Uninstall now reports the restoration failure explicitly, retains its active
installation record and backups, and tells the user to retry after resolving
the error. The restoration helper explicitly handles directory/temporary-file
creation errors and removes temporary copies after failed atomic replacement.

Validation passed:

- `python3 -W error tests/installer-rollback.py`: 18 isolated cases, including
  failures creating the directory/temporary file, copying or replacing prior
  state, and removing initially absent state, in both rollback paths.
- Failure checks cover retained preference/override/backups, absence of false
  success reports and temporary-file leaks, and successful uninstall retry.
- `bash tests/installer-state.sh` and `bash tests/shell-profile.sh` (including
  22 invalid overrides), Bash syntax checks, and `git diff --check`.

These tests use read-only host mounts, writable temporary fixtures and simulated
services. They do not validate real systemd/SDDM timing, standalone-install
parity, every cleanup failure, or new graphical behavior. No VM, real service,
package build/install, host configuration or trust changes were performed.

Next KDE-only work: review remaining partial installer changes and standalone
parity, then reconcile package metadata/checksums with a new revision and run
reproducible builds and fresh disposable-VM lifecycle validation. Keep the
menu-only KDE profile as the demonstrated baseline; non-menu profiles remain
experimental/unvalidated. This checkpoint is not a newly validated release.

## 2026-09-23: KDE installer parity and preservation review

Resumed from `47cc226`. Scope remained the KDE-only proof of concept, with
no host adoption or additional desktop/plugin work.

Review fixes:

- Standalone setup now includes the same inert Bar import symlink as the KDE
  package. The recorded VM QML failure established why loading requires this
  even though the menu-only profile does not instantiate an Omarchy bar.
- Setup refuses pre-existing SDDM override and integration paths, including
  dangling symlinks. Standalone conflict checks now include both new helper
  libraries, avoiding overwrites and later removal of pre-existing files.
- Packaged setup prints the working `frankenstein uninstall` command instead
  of a nonexistent `uninstall.sh` path. Test fixtures now use the actual
  packaged `setup` and `uninstall` filenames.
- SDDM preflight now reads vendor fragments, local fragments, then the main
  configuration file, matching the installed SDDM 0.21.0 manual. It handles
  whitespace around values and previews the proposed fragment in that order.
  Higher-precedence settings that defeat the proposed override cause a refusal
  before mutation; existing administrator configuration is not rewritten.

Validation:

- `python3 -W error tests/installer-rollback.py`: 56 cases passed across
  packaged and standalone layouts (36 lifecycle/failure cases, 12 conflict
  cases and 8 SDDM precedence/preflight cases).
- Lifecycle fixtures verify unchanged KDE settings and matching archive copies
  for panel layout, display output, session, power and Qt configuration; active
  KDE default selection; standalone payload removal versus package retention;
  and the existing restoration/retry checks.
- Existing installer-state and shell-profile suites passed (including 22 invalid
  profile overrides), as did Bash syntax and `git diff --check`.
- INSTALL.md now describes conflict handling, incomplete recovery and the
  distinction between earlier VM evidence and current source-only testing.

Limits: service/package/default-writer commands remain simulated. These checks
exercise real installer/uninstaller control flow and file operations, not QML
loading, real systemd timing, all failure points, package installation or
arbitrary SDDM configuration syntax. No VM was started and no host configuration,
service, package database, repository or trust was changed. Unrelated untracked
ISO/boot reference files remain untouched.

Next step: reconcile package source checksums and `.SRCINFO`, assign a fresh
revision, build reproducibly, then validate those exact KDE packages in a fresh
baseline-backed VM. Preserve menu-only scope. This checkpoint is not a new
validated package release.

## 2026-09-23: preserve the user's current KDE/Omarchy baseline

The user clarified that whatever Omarchy features are active now must remain
active under KDE. This supersedes the earlier instruction to treat menu-only
scope as sufficient for host adoption. KDE remains the only desktop target.

Read-only host inspection found Plasma Wayland already running alongside the
enabled, active `omarchy-shell.service`, launching the stock Omarchy shell.
The live shell's read-only `listPlugins` response reported 31 enabled entries,
including the Omarchy bar and seven third-party plugins: Invaders, Tetris,
Plug, Recall, Tutor, World Radio and DistroWatch Rankings. The bar configuration
also includes a custom local service-status command widget, which is not a
plugin-registry entry and must not be lost during adoption.

The user's explicit disabled list is workspaces, idle, lock, nightlight and
monitor. Preserve those choices; this request does not mean enabling every
installed component. Registry enablement is not proof of functional ownership:
for example, Notifications is enabled in the shell registry, while the current
`org.freedesktop.Notifications` bus name is owned by Plasma. Do not force an
ownership change or assume every enabled feature has been validated.

A local sanitized baseline inventory was saved in this task's outputs as
`kde-omarchy-baseline.json`: enabled IDs, layout IDs, disabled IDs, service state,
observation time and shell-config fingerprint. Raw plugin settings and custom
command contents were not copied into the repository.

The current setup path would disable the existing shell service and use the
menu-only profile; it therefore does not meet this clarified acceptance
criterion. INSTALL.md now states this limitation. No host settings, plugin
states, services, package configuration or trust were changed, and no adapter
was installed or launched.

Next work must design and test adoption that preserves the observed enabled
features, disabled choices and custom widgets without duplicate shell instances
or silently replacing functionality. First classify the observed components
and ownership, then implement and validate in an isolated KDE environment.
The earlier VM menu-only results remain valid only for that narrower profile.
Do not advance to host installation based on them or treat profile-merge unit
tests as graphical validation of this broader preservation requirement.

## 2026-09-23: preserve existing settings and offer selective choices

The user requested Frankenstein's benefits without losing current settings,
then clarified that optional selection must include individual plugins/widgets
and a custom widget. This supersedes the prior menu-only adoption scope.
KDE remains the only target; no host installation was performed.

Implemented in source:

- Setup defaults to `--shell auto --login preserve --default keep`. Existing
  Omarchy shell services keep their configuration and active/enabled state;
  no replacement shell/autostart is created. Without an existing service,
  auto still installs the filtered menu-only adapter.
- Login theme/autologin and remembered desktop remain unchanged by default.
  The default-session watcher is installed but has no preference to enforce
  until the user selects one. Existing default-manager state is refused as a
  conflict rather than overwritten.
- Independent explicit choices are `--shell preserve|filtered`,
  `--login chooser`, and `--default auto|omarchy|plasma`. Choosing filtered
  explicitly replaces the service, while retaining original config files and
  restoring the original service state on rollback. Preflight describes this
  reduction; it is never silently chosen for an existing service.
- Installation records persist shell ownership. Uninstall and rollback leave
  preserved shell services and user files alone. Adapter run/enable/disable
  refuse to replace a preserved shell; menu IPC targets the stock shell, and
  checks report availability without claiming plugin compatibility.
- `frankenstein desktop` exposes the existing chooser/default/switch controls.
- `frankenstein settings` provides opt-in per-plugin/per-widget selection from
  the running stock shell and explicit bar layout. Everything starts selected;
  keeping everything is a byte-for-byte no-op. Custom command widgets and
  repeated instances are included; retained entries keep all their fields.
  Disabled plugins stay disabled. The bar itself is not deselectable.
- Deselecting a plugin disables it and removes linked widgets; deselecting a
  widget removes only that occurrence. No new plugin is enabled. A diff and
  typed APPLY are required, an original-file backup is saved, and detected
  concurrent changes are refused. Commands inside widgets are never executed
  by selection. A read-only catalog and preview are available separately.

Validation:

- 56 existing isolated installer/rollback cases passed.
- 16 new packaged/standalone preservation and independent-category cases
  passed, including failure/retry, inactive-service preservation, unchanged
  config/plugin/script files, and no unsolicited shell service mutations.
- 9 selection tests passed: custom widget fields and duplicate instances,
  keep-all exact no-op, selective changes, cancellation, invalid selections,
  preview-only behavior, original backups, concurrent edits and refusal of
  symlinks/unsupported configurations. Widget commands were not executed.
- Existing installer-state and shell-profile suites (22 invalid overrides),
  Bash syntax checks and `git diff --check` passed.
- A read-only catalog/keep-all preview on the current host recognized the
  custom `local-rp-status` widget. The shell.json SHA-256 remained
  `e7fd16b4c4ffb58b34181b12738e7792512e3c454fc548f65f3e81fb798c4b5a`.
  No selection was applied and no user service was changed.

Packaging has source/install entries for the new settings command and its
explicit gum/diffutils dependencies. Checksums, revision and `.SRCINFO` still
need reconciliation before building; no package from this tree was built or
installed. This is local source/control-flow validation, not graphical proof
of all 31 currently enabled entries. The selection UI was tested with mocked
input, not a live interactive apply on the user's desktop.

Next: reconcile and build packages with a new revision, then test both fresh
menu-only setup (explicit chooser/default options) and existing-shell
preservation in a disposable KDE VM. Test custom-widget selection there before
any host use. Existing autologin can still override desktop choice when the
user elects to preserve it; report that limitation rather than changing it
silently. Keep all host settings and plugin states unchanged until a separately
reviewed host installation plan is approved.

## 2026-09-23 — Revision 5 disposable-VM validation

Built the source at `a072ab2` twice with reconciled revision/checksums; both
clean builds produced identical unsigned package hashes:

- core: `b41a3f75a0a1c84d8a276710ce1aff069803dd09b155b2f998b12e951b418292`
- kde: `975fd3daf45c08663f7278d2113c4b9ad2a1269ef3ccbbacfd0ae9950d65c67b`

Installed both 0.1.0-5 packages in a fresh overlay backed by the preserved
Omarchy baseline. Explicit chooser/default setup and filtered Plasma login
passed, with menu IPC and native Plasma panel/portal. A VM-only existing-shell
fixture then exercised preservation: unchanged shell config, custom command
widget, service file, active PID and SDDM files after default setup. Keeping
everything in the real selection UI was a bytewise no-op. Interactive selective
apply disabled Background, then removed the audio widget while retaining the
custom widget and its fields; original backups were created. No user host
selection was applied.

Preservation survived Plasma logout/login with exactly one stock shell. After
restarting the VM and returning through Omarchy to Plasma, the custom config
remained byte-identical to the selected result. Uninstall and actual pacman
removal of both packages left Plasma and the original shell active with one
instance and retained the selected settings. A cached shell command lookup
after removal was misleading; fresh filesystem/package checks confirmed the
executable, helper directory and both packages were absent.

**Release blocker:** the synthetic preserved service and Omarchy's native shell
launcher race on Hyprland login. The first return logged “An instance of this
configuration is already running” and left the service inactive while IPC
worked. On a subsequent boot both launchers started separate stock-shell
instances. Revision 5's preservation check does not count instances, so an
active service plus IPC can falsely pass that duplicate state. Returning to
KDE yielded one instance. Do not claim preserved-shell round-trip support or
install on the host based on these results. Preserve-mode installation did
not create this service; the test fixture deliberately supplies it as existing
configuration. Fixing ownership must respect the user's preservation choices.

81 local installer/preservation/selection cases and both shell helper suites
passed again (including 22 invalid profile cases). Offline overlay integrity
check passed before reopening. Evidence is under `evidence/kde-0.1.0-5/`,
including `guest-logs.tar.gz`, screenshots and build log. These tests cover a
representative custom widget, not every enabled third-party plugin or the
user's exact widget command. Revision 5 is an unsigned test build, not a
validated public release. Host config, services, packages and trust unchanged.

## 2026-09-23 — Refuse a misleading preserved-shell health pass

The source health check now requires exactly one Quickshell instance for the
stock config on the current display, in addition to active service and working
IPC. Query failure/malformed output fails conservatively. It reports unresolved
ownership without starting, stopping or rewriting an existing service. Seven
isolated health scenarios passed, including duplicate/zero instances, query
failure, inactive service and unavailable IPC. The same function passed against
the running VM's single Plasma shell after package removal. This diagnostic
fix does not resolve the Hyprland dual-launcher race.

Reserved revision 6 and refreshed source checksums/metadata to avoid changing
the frozen revision 5 artifacts. Revision 6 is not built or VM-package-validated
yet. The next implementation task is an explicit, reversible ownership policy
for an existing shell service across KDE/Omarchy sessions, followed by repeated
login and reboot testing. Do not silently rewrite the preserved service.

Validation cleanup: copied the guest logs to the local evidence archive,
removed temporary guest SSH authorization, sudoers allowance and firewall
rule, and shut down the disposable VM. Final offline image check passed.
The preserved baseline SHA-256 still matches
`844be5c310a5750902c40d1ab95fb5144b6788b29cbfa7d3b96b29aaa253c4c0`.

## 2026-09-23 — Reject malformed preserved-shell instance records

Resumed from `c8630c3` with a clean tracked tree. The public chooser checkout
contains an older journal copy; this task changes only this adoption checkout.
Completed one bounded follow-up to the existing preserved-shell health check:
reject malformed instance records rather than reporting a healthy shell merely
because the returned array contains one element. Six new cases first reproduced
false passes. The parser now requires exactly one JSON document containing an
array of objects with positive integer PIDs. Extra fields remain accepted;
invalid/query-failure results report unknown instance count and unresolved
ownership. Zero and multiple valid instances still fail the health check.

Validation:

- Preserved-shell health matrix: all 17 scenarios passed, including malformed
  records, invalid/empty JSON, multiple documents and forward-compatible fields.
- All 16 isolated preservation/selection installer cases passed after supplying
  the missing instance-list response in their simulated Quickshell fixture.
- Shell-profile suite passed, including all 22 invalid override cases.
- Adapter Bash syntax and `git diff --check` passed.
- A read-only instance listing confirmed the installed Quickshell reports a
  numeric `pid`; no shell IPC action or service mutation was performed.

Refreshed PKGBUILD checksums and `.SRCINFO`. Revision 6 remains the already
reserved, unbuilt revision; no frozen package bytes were reused or published.
No VM, package build/install, host configuration, services, trust, pacman
repositories or SDDM state were changed. Existing custom settings, optional
Omarchy bar/components and the conservative fresh menu-only default are intact.
The three pre-existing untracked ISO/boot references were left untouched.

The Hyprland dual-launcher ownership race remains unresolved. Next smallest
task: document the explicit reversible ownership policy and its acceptance
cases before implementing service lifecycle changes. Revision 6 still needs
reproducible builds and disposable-VM validation; this diagnostic correction
does not certify plugin compatibility or preserved-shell round trips.

## 2026-09-23 — Reversible shell-ownership policy documented

Resumed from `4268a81` with a clean tracked tree. Completed only the documented
next task: define the ownership policy and acceptance cases before service
lifecycle implementation. Added `docs/SHELL-OWNERSHIP.md`, linked from README.

The proposed contract keeps auto/preserve behavior unchanged and requires a
separate explicit opt-in for future managed ownership. Plasma would have one
Plasma-scoped owner using the reviewed preserved configuration; Omarchy keeps
its native launcher. Unknown units, competing activation paths and ambiguous
sessions must be refused rather than guessed. Exact activation/recovery state,
mutation ordering, concurrent edits, retryable failures and session-safe
restoration are specified. Restoring enablement does not imply immediately
starting a service alongside Hyprland's native shell.

The contract retains customized top bars, plugins, widgets and disabled choices.
Menu-only remains the fresh conservative default, not the only intended profile.
It separates lifecycle health from plugin compatibility and lists local failure
cases plus repeated real login/reboot acceptance cases. These requirements are
proposed behavior, not new command-line options or claims of passing VM tests.

Validation: all 16 isolated preservation cases and 17 preserved-shell health
scenarios passed; local Markdown links and `git diff --check` passed. Reviewed
the current installer, uninstaller, adapter, service and autostart definitions
against the document's current-behavior description. No production code or
package payload changed; revision 6 and its checksums remain unchanged. No VM
was started and no host configuration, service, package trust, pacman repository
or SDDM state was modified. The three unrelated untracked references remain.

Next smallest task: implement a read-only ownership inventory for one narrowly
recognized service shape, with disposable fixtures that reject alternate
activation paths and unsupported overrides. Do not implement lifecycle mutation
in that task. The dual-launcher race, managed ownership implementation,
reproducible revision 6 builds and disposable-VM package validation remain
unfinished. No host adoption is authorized by this design checkpoint.

## 2026-09-23 — Offline shell-ownership inventory

Resumed from `a53597a` with a clean tracked tree. Completed a bounded first
implementation of the documented read-only inventory: the development-only
`tools/shell-ownership-inventory.py` assesses explicit disposable directory
snapshots. It recognizes the direct Quickshell service shape already used by
`tests/preserve-shell.py`, with either its single known activation link or no
link. It emits JSON file hashes/modes, link targets, observations and refusal
reasons. It does not execute commands, use implicit host paths, follow discovered
links, write configuration or authorize migration. `migration_ready` is always
false; recognized shape refers only to the supplied snapshot.

Additional units, autostarts, drop-ins, aliases, masks, wrappers, unknown links,
missing inputs, special files and invalid text are rejected conservatively.
This intentionally does not interpret general systemd syntax or assert that
all real activation sources were captured. The ownership document describes
usage, exit statuses, stable-snapshot requirements and these limitations.

Validation:

- `python3 -W error tests/shell-ownership-inventory.py`: all 18 disposable
  fixture scenarios passed, including original input bytes/metadata retained,
  reported hashes checked and embedded commands never executed.
- `python3 -W error tests/preserved-shell-health.py`: all 17 existing health
  scenarios passed.
- `git diff --check`: passed.

No existing setup behavior, shell settings, optional bar/plugin support or
conservative fresh default changed. The assessor is not packaged or wired into
setup; package revision 6 and payload checksums remain unchanged. No host
configuration, services, package trust, pacman repositories or SDDM state were
modified. No VM or package build/install was performed. The three existing
untracked ISO/boot reference files remain untouched.

Next smallest task: add a read-only effective-unit metadata/search-path
collector with mocked systemctl responses, keeping assessment distinct from
migration authorization. Live session/process ownership, activation sources
outside snapshots, lifecycle changes, the cross-session race, reproducible
builds and disposable-VM validation remain unfinished. Do not begin lifecycle
mutation merely because this offline fixture shape is recognized.

## 2026-09-23 — Read-only effective-unit metadata collector

Resumed from `8f8048c` with a clean tracked tree. Completed the documented
metadata/search-path collection step as a separate development-only tool,
`tools/shell-ownership-metadata.py`. It performs only two bounded user-manager
`systemctl show` queries and emits JSON observations. Neither setup nor the
offline inventory invokes it automatically; it is not packaged.

Collected fields include unit identity/names, load and unit-file states,
fragment/source/drop-in paths, active/substate, reload requirement, raw launch
metadata and manager search paths. Simple path lists preserve order; ambiguous
serialization is retained raw and flagged. Missing/duplicate/malformed property
sets and query failures fail conservatively. Aliases, masks, overrides,
generated units, stale configuration and unsupported runtime states require
review. Successful collection never authorizes migration: `migration_ready`
remains false and no effective file shape or session ownership is certified.

Validation:

- Mocked metadata suite: four test methods covering 30 scenarios (two ordinary
  states, 11 review findings, 11 malformed/unsupported serializations and six
  query failures). Tests assert fixed read-only query arguments, timeouts,
  preserved observations, refusal behavior and no leaked failure output.
- Existing offline inventory: all 18 fixture scenarios passed.
- Existing preserved-shell health matrix: all 17 scenarios passed.
- `git diff --check`: passed.

All manager calls in the new tests were mocked; no real host systemd query or
service mutation was used. No host configuration, services, trust, pacman
repositories or SDDM state changed. Customized shell choices and the menu-only
fresh default are untouched. No VM or package build/install was performed;
revision 6/checksums remain unchanged. The three pre-existing untracked
ISO/boot references remain untouched.

Next smallest task: validate these query properties/serialization against the
disposable VM's real user manager and retain sanitized observations as fixtures.
The collector is not yet real-manager validated or combined with filesystem
assessment. Complete activation/session ownership analysis, lifecycle changes,
the duplicate-launcher fix, reproducible builds and VM package validation remain
unfinished. Do not infer migration readiness from successful metadata collection.

## 2026-09-23 — Guest metadata capture preparation checkpoint

Resumed from `9703880` with a clean tracked tree. The intended real-manager
validation requires the encrypted disposable VM and restoration of temporary
guest access removed during prior cleanup. This was not expanded into a VM
access/boot session. Two brief bubblewrap probes, with private runtime paths
and no host service access, confirmed that a real user manager could not start
in that environment (missing systemd boot context, then cgroup hierarchy).
No VM was booted and no real-manager validation is claimed.

Stopped at a bounded preparation checkpoint: added the guest-side development
runner `tools/capture-shell-ownership-metadata.py`. It executes the existing
read-only collector and saves its report and exit status in a new mode-0600
JSON file, refusing overwrite/symlink destinations. Evidence is explicitly
marked unsanitized; no manufactured observation is presented as a VM fixture.
The ownership document describes execution and the remaining validation limit.

Validation:

- Eight end-to-end capture cases passed with a fake systemctl on an isolated
  PATH: active/inactive, drop-in, query failure, malformed output, existing
  file, symlink and missing parent. Tests verify only the two allowed show
  queries execute, statuses survive capture and file permissions are private.
- Existing metadata suite: four methods / 30 scenarios passed.
- `git diff --check`: passed.

No setup or package payload changed. Optional bar/components, custom widgets,
disabled choices and fresh menu-only defaults remain intact. Host configuration,
services, package trust, pacman repositories and SDDM state were not modified.
No package was built or installed. The original untracked reference files were
left untouched. This checkpoint completes capture preparation only.

Next smallest task remains real-manager validation: boot the disposable guest,
run this capture tool for existing supported states, sanitize observations and
retain replay fixtures. Guest access/unlock must be available for that session.
Effective-unit integration, session/activation assessment, lifecycle ownership,
the duplicate-launcher fix and package/VM release validation remain unfinished.

## 2026-09-23 — Real user-manager property observation

Resumed from `57c6677` with a clean tracked tree. Created a new disposable overlay
backed by the prior revision-5 test image (itself baseline-backed), separate
firmware variables and a small data disk. Networking was disabled; preserved
images remained backing files. Disk unlock and desktop autologin succeeded.
Serial account authentication did not; no guest credentials were changed.

Executed the collector's exact two read-only `systemctl --user show --all`
property queries from the guest desktop. Systemd identified itself as
261 (261.2-1-arch). The existing service was enabled/active/running, with the
expected identity, fragment, empty source/drop-in paths, no reload requirement
and populated ExecStart metadata. UnitPath contained 17 ordered absolute paths.

Retained a sanitized, explicitly transcribed observation at
`tests/fixtures/shell-metadata/systemd-261-active.json`, with provenance and
normalizations in its README. A replay regression confirms those observed
properties parse successfully without implying migration readiness.

Validation: metadata suite passed (30 existing scenarios plus the real-output
fixture replay); all eight capture tests passed; `git diff --check` passed.
These validate real query serialization plus local collector replay, not full
collector/capture execution in the guest. A long console transfer was unreliable
and was abandoned to keep the session bounded. The guest also displayed the
known duplicate-bar limitation; no ownership fix was attempted.

No host configuration, services, package trust, repositories or SDDM state were
changed. No package was built or installed; optional shell components, custom
settings and the conservative fresh default are unchanged. No password was
saved in the repository or evidence files. The data-disk mount was dismissed
when it requested guest authentication; no temporary remote access was enabled.

Next smallest task: run the full capture runner in the disposable guest through
a reliable file-transfer path and collect one inactive-state observation. Full
capture validation, lifecycle ownership, the duplicate-launcher fix and package
release validation remain pending. This session stops at query-format validation.

Cleanup: desktop shutdown input and a virtual power-button request did not stop
the guest promptly. Terminated only this disposable QEMU through QMP, then ran
an offline `qemu-img check`, which passed. This is container-format integrity,
not a clean guest-filesystem shutdown claim. Scratch overlay and console evidence
are retained under ignored `evidence/metadata-261/session/`; no live VM remains.
Do not use this forced-stop overlay as a release-validation baseline.

## 2026-09-24 — Full guest metadata capture validated

Resumed from `ec1cc6d` with a clean tracked tree. Completed the remaining full
capture-runner validation in a new disposable overlay backed by the preserved
revision-5 image, not the prior forced-stop overlay. Used separate firmware
variables and an automounted removable test disk containing the unchanged
collector and capture runner. No network device or remote access was enabled.
Disk unlock and graphical autologin provided access; no credentials were saved.

On systemd 261 (261.2-1-arch), the complete capture runner produced mode-0600
reports for the existing enabled service in active/running and, after a
guest-only stop, inactive/dead states. Both collected all requested metadata,
returned exit status 0 and kept `migration_ready=false`. Enablement was never
changed. SHA-256 verification confirmed unchanged guest shell.json and original
service-unit bytes.

A guest-only restart attempt was also captured: the service remained enabled
but was inactive/dead, with its command reporting exit status 0. Do not describe
this as successful active-state restoration. Its cause was not investigated in
this bounded task; the existing duplicate-launcher limitation remains unresolved.
Successful metadata collection does not mean shell health or migration readiness.

Retained three sanitized full capture fixtures and their provenance under
`tests/fixtures/shell-metadata/`. These are machine-produced reports, separate
from the earlier console transcription. Sanitization changes home paths, PIDs
and times only, and marks each retained copy sanitized. Added replay assertions
for all three reports, including enabled-but-inactive behavior, and updated the
ownership document's validation status and remaining work.

Validation:

- Metadata suite: six methods covering 30 synthetic scenarios, the previous
  transcribed observation and three real capture replays; all passed.
- All eight end-to-end mocked capture cases passed.
- Guest configuration hash checks passed; capture reports retained mode 0600.
- Guest unmounted its test disk and completed native systemctl poweroff. No
  QEMU process remains. Offline qemu-img check and read-only e2fsck passed.
- Preserved baseline SHA-256 remains
  `844be5c310a5750902c40d1ab95fb5144b6788b29cbfa7d3b96b29aaa253c4c0`.
- `git diff --check` passed.

Private evidence is under ignored `evidence/metadata-capture-20260924/`.
No production implementation or package payload changed; revision 6 remains
unbuilt. No host configuration, services, trust, pacman repositories or SDDM
state changed. Optional Omarchy components, custom widgets, disabled choices
and the conservative fresh menu-only default remain intact. The three unrelated
untracked references were untouched.

Next smallest task: connect captured effective-unit metadata to the offline
filesystem assessment with explicit source-path mapping and mismatch/refusal
fixtures. Keep it read-only and do not infer migration readiness. Complete
activation/session assessment, lifecycle ownership, the duplicate-launcher fix,
reproducible package builds and graphical package validation remain unfinished.

## 2026-09-24 — Offline captured-metadata consistency check

Resumed from `74458c1` with a clean tracked tree. Completed the documented
bounded task connecting the existing capture and snapshot assessments. The
inventory now accepts paired `--capture` and `--source-unit-directory` options.
The explicit original-directory mapping is compared as data and never opened.
Snapshot-only operation remains unchanged.

Saved raw properties are reassessed through the collector's existing rules,
using an injected offline query source instead of systemctl. Captured derived
fields must agree with that assessment. The comparison checks the exact mapped
fragment path, inclusion in the captured search path, recognized single-command
ExecStart serialization and enabled/disabled activation-link consistency.
Malformed/unsuccessful captures, duplicate keys, unsupported types, overrides,
stale-manager findings, wrappers and extra commands fail conservatively.

`consistent_observations=true` is explicitly not migration authorization.
`migration_ready` remains false. An enabled but inactive service can have
consistent metadata; this does not imply a healthy shell. Snapshot origin,
content correlation, freshness, other search-path contents, activation sources
and live session ownership remain unassessed. Updated the ownership document
with usage, output semantics and these limitations.

Validation:

- New consistency suite: 28 snapshot/capture scenarios and two missing-option
  cases passed. Includes all three real VM capture fixtures, disabled/no-link
  agreement, mismatches, refusal cases, unchanged input bytes/metadata and no
  execution of embedded commands. An empty PATH prevents host tool invocation.
- Existing inventory: all 18 fixture scenarios passed.
- Existing metadata: 30 synthetic scenarios and four observed-data replays passed.
- Existing capture: all eight end-to-end mocked cases passed.
- `git diff --check` passed.

No VM or real manager was contacted. No host configuration, services, trust,
pacman repositories or SDDM state changed. Customized components, optional top
bar/widgets, disabled choices and the conservative fresh menu-only default are
unchanged. No package payload changed; revision 6/checksums remain unchanged.
The three unrelated untracked references remain untouched.

Next smallest task: add fragment-byte provenance (hash and read outcome) to
metadata capture, with replacement/symlink/refusal tests. This would let the
comparison distinguish a captured unit copy from a supplied matching shape;
it must still not authorize migration. Broader activation/session assessment,
lifecycle ownership, the duplicate-launcher fix, reproducible builds and
package/graphical VM validation remain unfinished.

## 2026-09-24 — Fragment-byte provenance and comparison

Resumed from `c2d1853` with a clean tracked tree. Completed the documented
fragment-provenance task by adding opt-in `--hash-fragment` to the capture
runner. Default metadata-only capture remains unchanged. The optional record
contains the reported path and explicit read outcome; only successful reads
include a SHA-256 hash and byte count. No file contents are emitted.

The bounded reader rejects noncanonical paths, symlinks in every path component,
non-regular files, files over 1 MiB and read errors. It checks file identity and
metadata before/after reading and after reopening the original path. Detected
rewrites or replacements produce refusal without a hash. Incomplete metadata
skips the read. A refused fragment yields capture status 1 while retaining the
independent collector result and private evidence file.

The offline comparison now checks optional provenance against snapshot bytes,
path and size. Same recognized syntax with different bytes is refused. Legacy
captures report `fragment_bytes_match=null`; provided matching/refused provenance
reports true/false. This is observation consistency, not proof of freshness,
authenticity or manager-loaded bytes; migration readiness stays false. Updated
the ownership document with the opt-in behavior and these limits.

Validation passed using only disposable files and simulated queries:

- 16 fragment-reader cases, including file/parent replacement, same-file rewrite,
  symlink and special-file refusal, missing/oversized inputs and injected errors.
- 12 full capture CLI cases, including hash success/refusal and incomplete
  metadata, private output permissions and distinct capture/collector statuses.
- 38 comparison/option cases, including matching hashes, changed comments with
  otherwise valid unit syntax, mismatched hash/path/size/type and refused reads.
- Existing inventory (18 cases) and metadata (34 scenarios/replays) suites.
- `git diff --check`.

No VM, real manager or host fragment was accessed. No host configuration,
services, package trust, pacman repositories or SDDM state changed. Existing
customization, optional Omarchy components and the conservative fresh default
remain unchanged. No package payload changed and no package was built/installed.
The three pre-existing untracked reference files were left untouched.

Next smallest task: validate opt-in fragment hashing in the disposable VM and
retain a successful observation plus a same-shape/different-byte refusal case.
Do not expand recognized unit shapes or implement lifecycle changes in that task.
Real-VM hash validation, freshness, broader activation/session assessment,
lifecycle ownership, the duplicate-launcher fix and release validation remain
unfinished.

## 2026-09-25 — Disposable-VM fragment hashing and refusal replay

Located the public Python chooser at `d85d677`; its journal identifies this
separate adoption checkout as the implementation/evidence source. Resumed here
from `f8aec0d` (`Capture and compare shell fragment byte provenance`), with no
tracked changes. The three unrelated untracked ISO/boot references remain
untouched. This session completed only the documented fragment-hashing guest
validation task; no lifecycle or supported-shape expansion was attempted.

Acceptance: execute the unchanged full capture runner with `--hash-fragment`
in a fresh disposable guest, independently verify exact unit bytes and private
output mode, exercise comment-only byte mismatch refusal, retain sanitized
replay evidence, and verify unchanged guest configuration plus safe shutdown.
The initial expectation of an accepted exact-snapshot comparison was corrected
after observing the real unit's unsupported directives, rather than loosening
the checker to make the validation pass.

A new overlay used the preserved revision-5 image as its backing file (itself
backed by the clean Omarchy baseline), with separate firmware and a removable
test disk. No network device, host block device or host filesystem share was
attached. The user unlocked the guest through its window; no credential was
saved. The tools copied from `f8aec0d` ran under systemd 261 (261.2-1-arch).

Results:

- Capture and collector returned 0; evidence mode was 0600. The existing unit
  was enabled, active/running, and its 386 bytes hashed to
  `e7ed27417635e1347352cfe571a947e707f59e0cdb28dcaf8519e765a90a8703`.
- The first exact-snapshot acceptance assertion failed: the actual service
  contains Unit/Install sections, environment and restart directives outside
  the minimal recognized fixture shape. Hash comparison itself succeeded.
- Rerunning with explicit conservative-refusal expectations passed. Exact
  snapshot bytes produce `fragment_bytes_match=true`, but exit 1 and overall
  consistency false because the shape remains unrecognized.
- Prepending only `# Comparison-only comment\n` to the disposable snapshot
  produces `fragment_bytes_match=false` and an additional provenance mismatch
  reason. No service-unit or shell settings were edited; their independently
  computed before/after SHA-256 values matched. No service was stopped, started
  or reconfigured for this test.
- Both cases retain `migration_ready=false`. The activation link was a
  constructed comparison fixture, not a complete guest activation inventory.

Retained sanitized full capture, exact service bytes and both comparison
reports under `tests/fixtures/shell-metadata/fragment-261/`. The fixture README
records provenance and path/PID/time sanitization. New regressions replay both
full comparison reports with an empty PATH, assert byte-match versus shape
refusal independently, and verify unchanged inputs. A metadata regression
replays this capture through mocked queries. Updated the ownership document
with the real-unit limitation and next bounded task. Production implementation,
package payload and supported profiles did not change.

Validation passed:

- Fragment-reader suite: 16 cases.
- Full capture CLI suite: 12 mocked cases.
- Consistency suite: 38 existing cases plus two real guest report replays.
- Inventory suite: 18 cases.
- Metadata suite: 30 synthetic cases plus five observed-data replays.
- `git diff --check`.
- Guest test-disk unmount and native poweroff completed; QEMU exited with 0.
  Offline `qemu-img check` and read-only `e2fsck -fn` passed.
- Preserved baseline SHA-256 remains
  `844be5c310a5750902c40d1ab95fb5144b6788b29cbfa7d3b96b29aaa253c4c0`.

Private runner, raw results, initial failed expectation and disposable images
remain in ignored `evidence/fragment-capture-20260925/`. No VM remains running.
No host configuration, service, package trust, pacman repository or SDDM state
changed. Existing optional bar/widgets, customizations, disabled choices,
Plasma support and conservative menu-only defaults remain unchanged.

Limits: this validates real fragment hashing and mismatch detection, not an
accepted real-unit comparison, freshness, manager-loaded bytes, exhaustive
activation sources or exclusive ownership. The known duplicate bar was visible
under the guest's Hyprland session. No Plasma graphical test, package build or
release validation occurred; revision 6 remains unbuilt.

Next recommended medium-sized task: review and classify the retained real
service's exact dependency/environment/restart/activation directives, then add
bounded read-only recognition and adversarial refusal tests if justified. Do
not implement lifecycle changes in that task. Broader activation/session
assessment, reversible lifecycle ownership, the duplicate-launcher fix and
package/release validation remain pending. Stop after this checkpoint.


## 2026-09-25 — Recognize the exact retained shell-service shape

The public chooser was clean at `db94981`; its historical journal points to
this adoption implementation checkout. Resumed here at `f4f89fe` with no tracked
changes and three unrelated untracked ISO/boot references, all left untouched.
Selected only the documented real-unit classification task. Acceptance was
bounded read-only recognition, adversarial refusals, preserved historical evidence
and no migration authorization or lifecycle changes.

The inventory now recognizes the exact retained 14-line VM service alongside
the minimal fixture. Description, sections, directive order, two environment
assignments, launch command, dependency/condition, restart and installation
settings are fixed. Only comments, blank lines and ordinary edge whitespace vary.
Unicode separators/whitespace are no longer treated as ordinary INI whitespace.
The ownership document classifies each directive and its limits: neither generic
graphical-session dependencies nor a manager environment condition identifies a
current Plasma session. Recognition does not prove loaded manager properties.

Historical VM reports and capture bytes remain unchanged. Current offline replay
accepts the exact snapshot/capture pair, rejects comment-only byte mismatch, and
always reports `migration_ready=false`. No installer, package payload, shell
profile, optional bar/widget, disabled choice or configuration is changed.

Validation passed:

- Inventory: 18 existing cases plus 53 real-shape cases, covering enabled and
  no-link snapshots, comments/CRLF, every missing/duplicate line, changed values,
  unknown directives, wrappers, continuation, reordered directives and Unicode.
  Inputs retain bytes/mode/mtime; real-shape tests run with an empty PATH.
- Consistency: 38 existing comparison/option cases and two retained VM replays.
- Fragment reader: 16 cases; full capture CLI: 12 cases; metadata: 30 synthetic
  cases plus five observed-data replays.
- Python warnings treated as errors; `git diff --check` passed.

No failures remained. No new VM run was necessary for this offline recognition
change: existing real systemd-261 capture and exact fragment bytes were replayed.
This does not validate current loaded dependency/environment values, freshness,
full activation inventory, Plasma graphical behavior or exclusive ownership.
Revision 6 remains unbuilt; package/release validation remains pending. No host
configuration, service, package trust, pacman repository or SDDM state changed.

Next recommended medium-sized task: extend read-only capture/comparison to
assess the recognized shape's effective manager dependency/environment/type/
restart properties, with conservative serialization and disagreement tests.
Broader activation/session assessment, reversible lifecycle ownership and the
known duplicate launcher remain subsequent work. Stop after this checkpoint.

## 2026-09-25 — Bounded effective manager-property comparison

Confirmed `d37de92` (`Recognize reviewed VM shell service without authorizing
migration`) was still HEAD before editing. Read this journal, the ownership
contract and current tools/tests. The tracked tree was clean; the three unrelated
untracked ISO/boot references remain untouched. Work stayed in this adoption
checkout, which has no configured remote; no repository rename or publication
was attempted.

Completed one implementation task: add opt-in typed effective-property capture
and conservative offline comparison for the exact retained VM service. Acceptance
was a successful synthetic match with exact fragment provenance, meaningful
property disagreements and malformed/missing evidence refusing, unchanged legacy
behavior, and no service lifecycle operations or migration authorization.

Changes:

- `capture-shell-ownership-metadata.py --effective-properties` records 65
  allowlisted typed properties (30 Unit, 35 Service) through two bounded busctl
  get-property invocations. Identity, fragment/source/drop-in paths and reload
  state are correlated with existing metadata. Individual reads are not atomic.
- Typed JSON avoids a discovered systemctl-show limitation: empty structured
  arrays such as EnvironmentFiles may produce no line. Missing replies must not
  be inferred to mean an empty list. The collector distinguishes typed emptiness,
  missing/extra replies, invalid signatures/data, query failure and timeout.
- Inventory `--require-effective` requires this evidence, the retained VM shape,
  successful capture and matching fragment hash/size/path. Supplied effective
  records are checked even without the flag. Legacy captures retain their prior
  limited behavior without it; with it they refuse. The shape now has the explicit
  `unit_shape=retained-vm-v1` label.
- Checks cover expected explicit/implicit dependency and ordering sets, conditions,
  environment assignments and absence of environment files, service type, exact
  extended launch argv/flags, absent execution hooks, restart/backoff/exit-status
  policy, stop behavior, timeouts and start limits. Unknown values, duplicates,
  extra directives/drop-ins, stale observations and changed semantics refuse.
- `effective_properties_match` reflects all required comparison checks, never
  migration authorization. `migration_ready` stays false. No environment file,
  embedded command or mapped source directory is read/executed by comparison.

Validation passed:

- New suite: five acceptance cases (including reordered sets, untested/failed
  condition observations and an inactive disabled service); 260 per-property
  missing/changed/mistyped/invalid-data refusals; 24 additional adversarial cases;
  automatic checking of supplied evidence and legacy behavior; 16 typed-query
  protocol cases; six full capture CLI cases, including combined fragment hashing
  and typed capture; required-option validation. Inputs remain unchanged and
  offline comparisons use an empty PATH. Capture audit permits only the specified
  fake systemctl show and busctl get-property commands; evidence mode is 0600.
- Existing inventory (18 plus 53 cases), consistency (38 cases/options plus two
  historical VM replays), fragment reader (16), capture (12), and metadata (30
  synthetic plus five historical replays) suites passed with warnings as errors.
- A temporary private D-Bus session exercised actual busctl JSON framing for
  multiple string-array property replies. It did not access a systemd manager.
- CLI help/documentation flag checks, local Markdown links in the updated ownership
  document, Python syntax parsing and `git diff --check` passed.

There were no remaining test failures. Historical VM capture/fragment/report
files are unchanged; the new typed fixture is explicitly synthetic. Explicit
values derive from the retained service. Implicit user-service dependencies and
related defaults were reviewed against systemd 261 source and local manuals,
not measured in the guest. The candidate contract pins app.slice/basic.target,
shutdown ordering, 90-second start/stop timeouts and 5 starts per 10 seconds;
legitimate different defaults or graph edges conservatively refuse pending review.

No real service was queried, enabled, disabled, started, stopped, restarted or
migrated. No VM was started. No host configuration, service state, package trust,
pacman repository or SDDM state changed. Plasma Wayland, optional bar/widgets,
customizations, disabled choices and conservative menu-only defaults are unchanged.
No package payload changed; revision 6 remains unbuilt.

Remaining limits: the new property set/structured serialization and actual guest
defaults still need a read-only disposable-VM capture. This checkpoint does not
establish that the real retained service passes. Inherited manager/process
environment, unqueried resource/sandbox properties, freshness, manager-loaded
bytes, graph origins, exhaustive activation paths, session ownership and the
known duplicate-launcher race remain unassessed. Passing conditions or active
metadata are not required for configuration agreement and are not health claims.

Next recommended medium-sized task: collect these typed properties and exact
fragment provenance in a fresh disposable VM without changing service state;
retain sanitized replies, explain any refusal against real defaults/dependency
origins, and add successful-or-refused observation plus deliberate mismatch
replays. Do not broaden recognition merely to force a pass. Stop before lifecycle
ownership, migration, duplicate-launcher resolution or release validation.

## 2026-09-25 — User-requested stop before effective-property VM capture

Resumed from `db7cd35` with no tracked changes and the same three unrelated
untracked ISO/boot references. The public chooser remained at `db94981`.
Selected only the documented effective-property guest-validation task. It is
unfinished: no guest capture runner was executed and no effective-property
observations or comparison results were retained.

Prepared ignored local infrastructure in `evidence/effective-properties-20260925/`:

- Fresh `test.qcow2` overlay backed by preserved
  `evidence/kde-0.1.0-5/fresh.qcow2`, itself backed by `omarchy-kde.qcow2`.
- Separate `vars.fd`, no network device, no host block devices or filesystem
  shares. The user unlocked the guest directly; no credential was saved.
- `payload/` contains unchanged tools from `db7cd35` and `run.py`, a prepared
  read-only capture/diagnostic/comparison runner. `data.img` contains that payload.
- Guest mounting of the virtio test disk requested authentication. A separate
  `usb-data.img` copy was attached as removable USB storage to use the guest's
  normal removable-drive policy. No authentication policy was modified.
- The user first paused work, then explicitly requested that this VM be killed
  and the work checkpointed. QMP `quit` stopped only this VM, reporting
  `host-qmp-quit`; QEMU exited with status 0. No QEMU process remains, and this
  run's QMP socket was removed. This was not a clean guest shutdown.

Saved `tests/shell-effective-vm-replay.py` as an unfinished replay scaffold. It
will mock typed-query replies and compare retained observed/mismatched reports
without manager access. The expected fixture directory is
`tests/fixtures/shell-effective/systemd-261/`, which does not exist yet. Both
cases explicitly skip until capture evidence exists; this is not a validation
pass. Expected files are `capture.json`, `Unit-raw.jsonl`, `Service-raw.jsonl`,
`omarchy-shell.service`, `observed.json`, and `changed-restart.json`. Do not fill
these with synthetic data or loosen the comparison to obtain a pass.

Validation at this stop:

- Replay scaffold syntax passed; execution reported two explicit pending-evidence
  skips. No new guest/graphical/property validation passed or failed because the
  runner never ran.
- Offline `qemu-img check` on the new overlay: no errors.
- Read-only `e2fsck -fn` on original data.img: completed without findings.
- USB copy check skipped journal recovery and reported orphan_present with a
  clean orphan file. It was not repaired. Treat that copy as interrupted-use
  evidence; create a fresh payload disk on resume rather than claiming it clean.
- The baseline hash checked during preparation remained
  `844be5c310a5750902c40d1ab95fb5144b6788b29cbfa7d3b96b29aaa253c4c0`.
- `git diff --check` passed. Existing suites were not rerun for this stop-only
  checkpoint; their last results remain those recorded under `db7cd35`.

No production implementation, package payload, shell ownership/profile or host
configuration, services, trust, repositories or SDDM state changed. The known
extra guest bar remained visible and was not investigated. No service lifecycle
fix, migration or release work was begun. The three unrelated untracked reference
files remain untouched; ignored disk images and prepared runner remain local.

Resume with one task: read the latest history and this entry, create fresh
throwaway overlay/firmware/payload media from the preserved sources, and complete
read-only typed capture without changing service state. Prefer removable payload
media from startup. Retain sanitized actual replies and exact fragment bytes,
explain refusals, finish observed/mismatch replays, and verify native guest
shutdown plus offline checks. Guest property serialization/defaults, ownership,
duplicate-launcher resolution and release validation remain unfinished. Stop here
as requested; do not restart the VM automatically.

## 2026-09-25 — Effective-property capture validated in disposable guest

Resumed from `63503b5`, the user-requested interrupted-run checkpoint. Tracked
files were clean; the same three unrelated ISO/boot references remain untouched.
The public chooser remains clean at `db94981`. Completed only the documented
read-only effective-property guest-validation task: actual replies, exact unit
provenance, explained refusal, offline mutation replay and clean shutdown.

Created fresh overlay, firmware and payload media under ignored
`evidence/effective-properties-resume-20260925/`, backed by the preserved revision-5
image and clean Omarchy baseline. The interrupted previous images were not reused
or repaired. No network device, host block device or host filesystem share was
attached. The user unlocked the guest directly; no credential was saved. Presenting
the payload as removable USB from startup allowed normal guest automount. An
explicit mount attempt reported it was already mounted; no authentication or
policy workaround was needed.

The unchanged tools from `63503b5` ran under systemd 261 (261.2-1-arch):

- Capture and metadata collector both returned 0. All 65 typed fields were
  collected, including real structured arrays and duration/infinity values;
  evidence mode was 0600. A second pair of read-only typed queries agreed with
  the captured configuration/runtime values after identical sanitization.
- Unit bytes were 386 bytes with SHA-256
  `e7ed27417635e1347352cfe571a947e707f59e0cdb28dcaf8519e765a90a8703`.
  Independent before/after hashes of this file and shell.json agreed.
- Comparison returned 1, with recognized shape and fragment-byte match true,
  effective/overall consistency false, and only one refusal: `After`.
- Actual After was `app.slice basic.target home.mount graphical-session.target
  -.mount`. The candidate contract lacks home.mount and -.mount. All other
  compared settings matched. No drop-ins or NeedDaemonReload were reported.
- The service was enabled but inactive/dead, with its prior command exited at
  status 0. The desktop still displayed the known extra bar. Neither condition
  success nor capture success is a shell-health or exclusive-ownership pass.

Read-only follow-up diagnostics reported `WorkingDirectory=!/home/omarchytest`,
`WantsMountsFor=/home/omarchytest`, empty RequiresMountsFor/RootDirectory, and loaded
home/root mounts with empty fragment paths. The home mount source was
/proc/self/mountinfo. These observations are consistent with systemd's default
user working-directory and synthesized mount-ordering behavior. The fixture README
links the source review. Complete dependency-origin proof is still outside the
current evidence contract, so no comparison rule or accepted set was broadened.

Retained actual sanitized capture, separately queried typed replies, exact unit,
guest-produced comparison, runner validation and dependency diagnostics under
`tests/fixtures/shell-effective/systemd-261/`. Sanitization changes home paths,
PID and runtime timestamps only (plus the envelope's sanitized flag). An initial
path-redaction check caught a guest home path in validation hash-map keys; key
sanitization was corrected, the private conversion script made rerunnable, and a
regression now checks those keys and all retained data files. Original private
results remain unchanged.

Completed the formerly skipped replay scaffold. Three tests now run: provenance
and sanitization, typed query replay, and full comparisons for the original
observation plus an offline-only Restart=always mutation. The latter retains
After refusal and adds Restart refusal despite matching fragment bytes. Fixture
files remain unchanged; comparison uses an empty PATH and queries are mocked.
Both cases retain `migration_ready=false`. No synthetic observation is presented
as guest evidence, and no live service setting was altered to create a mismatch.

Validation passed:

- New actual-VM replay suite: all three tests, including both full comparison cases.
- Existing effective-property acceptance/refusal/protocol/capture suite.
- Existing inventory, consistency, fragment-reader, metadata-capture and metadata
  suites, with Python warnings treated as errors.
- Syntax, retained JSON, local documentation links, sanitization checks and
  `git diff --check`.
- Guest payload unmount and native poweroff; QEMU exited with 0. No QEMU process
  remains. Offline `qemu-img check` and read-only `e2fsck -fn` passed without findings.
- Baseline hash before and after the run remained
  `844be5c310a5750902c40d1ab95fb5144b6788b29cbfa7d3b96b29aaa253c4c0`.

The actual comparison refusal is intentional and preserved, not an unresolved
test failure. Capture serialization and refusal detection are validated, but an
accepted real-unit effective comparison is not. No production/package payload,
profile or lifecycle behavior changed; revision 6 remains unbuilt. No host
configuration, services, package trust, pacman repositories or SDDM state changed.
Plasma support, optional bar/widgets, customized/disabled components and the
conservative menu-only default remain unchanged.

Next recommended medium-sized task: extend bounded read-only evidence for
working-directory and mount-dependency origins, with adversarial tests separating
implicit home ordering from explicit/unrelated mount dependencies and overrides.
Only consider a narrowly justified recognition change after that evidence exists;
do not blanket-allow mount units. Freshness, inherited process environment, full
activation/session assessment, reversible ownership, the duplicate-launcher fix
and release validation remain subsequent work. Stop after this checkpoint.


## 2026-09-26 — Bounded supplementary mount-context capture

Resumed from confirmed HEAD `872edf9` (Validate typed shell properties against
disposable VM evidence). Tracked state was clean; the three unrelated untracked
ISO/bootstrap files were left alone. Selected one task from the documented next
step: implement bounded working-directory/mount context capture and offline
consistency diagnostics, without relaxing the retained After refusal.

Acceptance criteria: fixed read-only queries; typed and complete supplementary
evidence; correlation with existing fragment and effective observations;
meaningful missing/changed/override refusal fixtures; no ownership authorization.
Implemented --mount-context capture (requires --hash-fragment and
--effective-properties) with six fixed queries and 29 typed properties. Added
--mount-home offline mapping and a strictly supplementary consistency result.
Only the exact retained home/root ordering candidate can agree diagnostically;
missing/extra properties, unrelated mounts, changed working/root directories,
explicit mount fragments, drop-ins, reload state and cross-capture disagreements
refuse. Prerequisite failure skips the additional queries. Capture remains private
and exclusive; no paths from evidence are used to discover query objects.

Even diagnostic agreement preserves the After refusal, comparison exit 1,
effective/overall mismatch and migration_ready=false. The new context cannot
prove implicit dependency origins or user identity; equivalent explicit settings
may produce the same effective values. The candidate home mapping is deliberately
narrow. No existing recognition rule or ownership policy was broadened.

Validation passed with Python warnings treated as errors:

- Seven new mount-context tests, including 116 per-property refusal mutations,
  six-group protocol/error coverage, partial-query failures, offline comparison
  and mocked complete/prerequisite-failed/partial capture paths.
- Existing effective-property suite (6 tests), actual-VM replay (3), inventory
  (2), consistency (3), fragment provenance (2), metadata capture (1) and metadata
  (7). Existing acceptance/refusal cases continue to run within those suites.
- Documentation/CLI checks, Python syntax and git diff --check.

Supplementary fixtures are synthetic, informed by retained text diagnostics;
actual systemd-261 evidence is unchanged. No VM or host manager was contacted in
this session. The new grouped live capture, including extra identity/root-image
fields, remains unvalidated on a real guest. No host configuration, service,
package trust, pacman repository or SDDM state changed. Plasma Wayland, optional
bar/widgets, disabled/customized choices and menu-only defaults are unchanged.

Next medium-sized task: read-only validation of this new grouped capture in a
fresh disposable VM, retaining genuine typed responses and replay tests. Explain
any differences without broadening recognition. Origin proof, ownership transfer,
duplicate-launcher resolution and release validation remain subsequent work.
Stop after this implementation checkpoint.

## 2026-09-26 — Mount-context capture validated in disposable guest

Confirmed HEAD `2cf4018` and clean tracked state before work. Left the three
unrelated untracked ISO/bootstrap files untouched; public chooser remains clean.
Selected only the documented grouped mount-context VM validation task. Acceptance:
real fixed-query replies, accurate diagnostic/refusal behavior, retained sanitized
evidence and offline replay with meaningful mismatches. No production tool or
ownership recognition change was needed.

Created a fresh overlay, firmware and USB payload under ignored
`evidence/mount-context-20260926/`, backed by the preserved revision-5 image and
clean baseline. No network, host block device or host filesystem share was exposed.
The user unlocked the encrypted guest directly. Initial runner failed before any
capture because the payload root was not writable. Corrected the disposable
harness by attaching a second results disk prepared with a writable root and
copying the unchanged payload there; result directory/capture remained 0700/0600.
No host or guest service configuration workaround was used.

Actual systemd 261 (261.2-1-arch) findings:

- Capture and metadata collector returned 0; all 65 effective and 29 supplementary
  fields collected. Six repeated typed queries exactly matched supplementary data.
- mount_context_consistent=true with no supplementary reasons. Overall comparison
  returned 1 and still refused only After; effective/overall match false and
  migration_ready=false. The expected home/root ordering remains unaccepted.
- WorkingDirectory=!/home/test and WantsMountsFor=/home/test (sanitized mapping);
  RequiresMountsFor, RootDirectory and RootImage empty. Loaded shell/home/root
  units reported no drop-ins, pending reload or transient status. Home/root mounts
  had empty fragments, expected Where values, home source /proc/self/mountinfo
  and empty root source. Exact After membership matched the bounded candidate.
- Service active/running this time; this is not a health/exclusive-ownership pass.
  The known extra bar was visible and was not addressed.
- Exact unit SHA-256 e7ed27417635e1347352cfe571a947e707f59e0cdb28dcaf8519e765a90a8703
  (386 bytes); independent before/after unit and shell.json hashes unchanged.

Retained actual sanitized capture, all six repeated typed replies, unchanged unit,
guest comparison and runner validation under tests/fixtures/shell-mount/systemd-261/.
Added four replay tests covering provenance/sanitization, typed collection,
truncation of each actual query group and full comparisons for observed data plus
offline HomeMount.Where and Restart mutations. Both mutations add refusals and
invalidate supplementary agreement. Existing fixtures are unchanged. A test mock
initially emitted a blank line instead of zero replies for truncated one-property
queries; corrected the mock and all cases passed. No live mutation was performed.

Validation passed:

- Four new actual-VM replay tests, including six truncated-query cases and three
  full comparisons with empty PATH and immutable input checks.
- Seven synthetic mount-context tests; effective-property (6), prior actual-VM
  replay (3), inventory (2), consistency (3), fragment provenance (2), metadata
  capture (1) and metadata (7) suites, with warnings treated as errors.
- Python syntax, JSON/JSONL parsing, documentation links and git diff --check.
- Both removable disks unmounted, native guest poweroff and QEMU exit 0. Offline
  qemu-img check and read-only e2fsck passed. Baseline before/after SHA-256 remained
  844be5c310a5750902c40d1ab95fb5144b6788b29cbfa7d3b96b29aaa253c4c0.

The preserved After refusal is expected, not a failed validation. New live query
coverage is complete for this guest; implicit dependency origin, home identity,
freshness, changes between queries, manager-loaded bytes and process environment
remain unproven. Activation linkage is a constructed comparison fixture, not full
activation evidence. No host configuration, services, trust, repositories or SDDM
changed. Plasma Wayland support, optional bar/widgets, custom/disabled choices,
menu-only defaults and ownership policy remain unchanged; no package was rebuilt.

Next medium-sized task: bounded capture-coherence checks around sequential reads,
with adversarial change-between-read fixtures and explicit non-atomic limitations.
Preserve the After refusal and migration_ready=false; do not proceed into live
ownership, duplicate-launcher resolution or release validation. Stop here.
