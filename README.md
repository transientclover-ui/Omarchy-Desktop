# Frankenstein

Frankenstein is a conservative Omarchy multi-desktop inspection, management,
and recovery tool. Its verified v1 target is Omarchy 4.0.4 with KDE Plasma
Wayland and Omarchy/Hyprland sessions managed by SDDM 0.21.

It preserves both desktops. Plasma starts through its packaged
`plasma.desktop`; Frankenstein does not wrap Plasma in UWSM or remove
Hyprland. Inspection comes before mutation, existing configuration wins over
defaults, and uncertain ownership is reported instead of guessed.

## Release-candidate features

- `frankenstein inspect`, `doctor`, and `verify` provide read-only human or
  stable JSON reports covering sessions, layered SDDM configuration, ownership,
  and agent-readable state.
- `install`, `switch`, `recover`, and `repair-sddm` expose the established
  explicit-approval setup, default-session, and rollback paths. The earlier
  `setup`, `desktop`, and `uninstall` names remain available.
- Plasma starts a Frankenstein-owned, session-scoped Omarchy Shell adapter.
  Fresh Plasma profiles receive the top bar alongside the stock KDE panel,
  with no first-party Omarchy widgets enabled; existing Plasma layouts retain
  the native-panel profile unless the user opts in. User-installed widgets
  remain eligible, while Hyprland keeps the untouched stock shell.
- A Frankenstein-owned SDDM theme makes the session selector the primary
  control and includes ordinary login, keyboard navigation, and visible power
  actions.
- On a fresh account with no meaningful appearance choice, setup initializes
  the subdued `Frankenstein Dusk` KDE color scheme, the project wallpaper, and
  Qt's available `Windows` application style and X.Org Whiteglass cursor once.
  Existing choices win, and the one-shot initializer never reconciles or
  reapplies a changed setting.
- The complete visual identity is declared in
  `/usr/share/frankenstein/presets/dusk-9x.json`; assets, functional shell
  integration, and user-owned runtime configuration remain separate.
- Matching Omarchy palette files are installed as optional project assets but
  are not forced over the user's active Omarchy theme.
- Memphis98 is not redistributed because its licensing is unclear. The
  permissively licensed X.Org Whiteglass theme provides the Windows 9x-style
  cursor fallback; the unverified Tumi and Microsoft-derived Chicago95
  conversions are excluded. KDE's icon default remains in place when no
  licensed candidate is available.
- The bundled default is a project-owned soft vaporwave background. A
  post-login graphical importer validates local PNG, JPEG, or WebP images and
  stages them in a greeter-readable collection. The login-screen gear can
  choose only bundled or staged images.
- Missing, unreadable, or invalid custom backgrounds fall back to the bundled
  image. The greeter never traverses private user homes.
- Setup backs up the exact SDDM and desktop state it changes and does not
  restart SDDM, log out, reboot, or remove a desktop.

The background import split is intentional. SDDM 0.21 themes have no supported
API for safely browsing a logged-in user's private home or running an arbitrary
helper. File selection therefore occurs after login under the user's authority;
the unauthenticated greeter only selects validated staged files.

## Known-bad release candidate

`v0.1.0-rc.1` is unsafe and must not be activated. Its SDDM metadata omitted
`QtVersion=6`, so SDDM selected the optional Qt 5 greeter on the dogfood host.
That host had the supported Qt 6 runtime but not the optional Qt 5 runtime;
`sddm-greeter` exited because `libQt5Quick.so.5` was unavailable, producing a
black screen. The tag and commits remain preserved as failure evidence.

## Quick start

Use the release installer with both matching local packages. It runs
`omarchy update -y` before pacman or desktop configuration, stops on any update
failure, and stops with exit 75 when a reboot boundary is detected. It never
reboots or restarts SDDM:

```bash
./install-frankenstein.sh \
  ./frankenstein-core-*.pkg.tar.zst \
  ./frankenstein-kde-*.pkg.tar.zst \
  -- --login frankenstein
```

After installation, the read-only checks remain available:

```bash
frankenstein inspect
frankenstein preflight --login frankenstein
```

The preflight is read-only. Installation prints the complete plan and requires
`INSTALL` unless the test-oriented `--yes` flag is supplied. It never restarts
the display manager. Log out normally only after saving work.

Useful read-only commands:

```bash
frankenstein inspect
frankenstein doctor --json
frankenstein verify
frankenstein settings --list
```

Use `frankenstein background` after login to import an image through a
graphical local-file chooser. Use `frankenstein switch` to choose a supported
default desktop. Use `frankenstein recover` before removing packages to restore
the recorded pre-install state.

## Safety and ownership

Frankenstein never silently removes KDE, Plasma, Omarchy, or Hyprland; resets
PAM or keyring state; deletes `state.conf` merely because it is old; or treats
`RememberLastSession` as corruption. Autologin, a hidden chooser, an invalid
session target, and a failed selected session are reported as distinct
conditions.

The ownership report distinguishes Frankenstein-owned, Omarchy-owned,
KDE/Plasma-owned, SDDM/system-owned, user-owned, and ambiguous paths. Evidence
is not authorization: ownership metadata and
`~/.local/state/frankenstein/sddm-state.json` are revalidated against the
filesystem and effective SDDM configuration.

See:

- [`INSTALL.md`](INSTALL.md) for approval, backup, and recovery behavior
- [`docs/STATE.md`](docs/STATE.md) for the non-sensitive state format
- [`docs/SHELL-OWNERSHIP.md`](docs/SHELL-OWNERSHIP.md) for shell provenance and
  refusal boundaries
- [`PLAN.md`](PLAN.md) for the finite v1 release-candidate boundary
- [`COMPATIBILITY-JOURNAL.md`](COMPATIBILITY-JOURNAL.md) for implementation and
  validation evidence

The `v0.1.0-rc.1` GitHub prerelease is preserved as known-bad evidence. This
checkout contains unpublished containment fixes and is not an OmaStore package.

## Development model

This project is “2D-printed”: behavior is specified, implementation is
fabricated with AI assistance, and the result is tested, inspected, and
iterated against conservative safety contracts.

The [login watchdog](docs/WATCHDOG.md) records startup failures before one bounded
shell recovery attempt. Use `frankenstein watchdog incidents` or
`frankenstein watchdog tail` to inspect local flight recorders.
