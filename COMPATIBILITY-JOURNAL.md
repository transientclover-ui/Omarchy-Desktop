# Omarchy Desktop Compatibility Journal

This journal was copied from the separate `work/vm` adoption checkout at
commit `0cfd79f` during public naming reconciliation. Historical source paths,
commit IDs, evidence and recovery-image paths below refer to that checkout,
not to files shipped in this Python chooser repository. Historical results
apply only to the recorded revisions and profiles; the later partial work is
not release-ready. This copy preserves the original entries as evidence.
**Omarchy Desktop** is the public project name. `Frankenstein` is retained
below only where it was an internal development codename or a literal historical
package, command, service, path, image, or repository identifier.

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

## 2026-09-23: public naming and documentation reconciliation

The public Python chooser repository was clean at `3d0dd1f`. It is distinct
from the VM adoption checkout at `0cfd79f`, whose journal was read first and
copied here with provenance. The adoption checkout was left unchanged.

Public README, CLI display headings and package description now use
Frankenstein. The introduction preserves “Choose your desktop. Keep Omarchy
shell.” and adds “Frankenstein isn't the monster. It makes the monster.”
README, compatibility documentation, testing notes and planning distinguish
completed KDE/Omarchy VM work from partial, unvalidated host-adoption work.
The CLI compatibility registry and all approval/safety behavior are unchanged.

The repository link and local origin now use `transientclover-ui/frankenstein`.
The Python module `omarchy_desktop`, distribution and executable
`omarchy-desktop`, and historical adoption paths remain unchanged for
compatibility and evidence accuracy. Omarchy/desktop keywords were added to
the README and package metadata; GitHub About description and topics were
updated for discoverability. No search-ranking guarantee is implied.

Validation: all 22 unit/fixture tests passed; isolated wheel build/install and
installed entry-point version, fixture JSON, branding and inspection-only gate
checks passed outside the source tree. Package keywords, local Markdown links
and `git diff --check` passed. No VM, host configuration, services, packages,
trust, pacman repositories, SDDM or desktop configuration were changed.
No adoption implementation or package release was advanced.

## 2026-09-23 — Restore public description

At the user’s request, restored Omarchy Desktop in the README introduction,
package description and CLI/prompt headings, and removed the Frankenstein joke
and branding keyword. The GitHub repository URL remains
`transientclover-ui/frankenstein`; no repository rename was requested.
Stable package/command identifiers and validation claims are unchanged.

## 2026-09-23 — Reconcile restored GitHub repository name

Confirmed GitHub now identifies the repository as
`transientclover-ui/Omarchy-Desktop`. Updated the current README link and local
origin to the canonical URL. Earlier journal names, artifact paths and package
identifiers remain historical evidence. Published the pending documentation
reconciliation without changing compatibility gates or host configuration.
