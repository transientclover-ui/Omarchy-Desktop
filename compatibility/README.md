# Omarchy shell compatibility

This project aims to offer every widely used desktop **once a specific
combination has passed Omarchy shell integration tests**. Installing a desktop
on Arch Linux is not the same as preserving the Omarchy shell experience.

## Current evidence

There are currently **no registered exact-version reports in the CLI registry**.
The [compatibility journal](../COMPATIBILITY-JOURNAL.md) records validated
KDE/Omarchy VM integration with a filtered menu profile and native Plasma
replacements, plus package lifecycle and signed repository tests. This bounded
work does not certify the full checklist below. Later partial host-adoption
changes still need package and disposable-VM validation.

CLI unit tests validate the chooser, not graphical desktop compatibility.
Install and switch requests remain inspection-only until a reviewed,
version-matched report is registered. Recovery and SDDM diagnosis remain available.

| Candidates | Current status |
| --- | --- |
| KDE Plasma | Filtered menu profile validated in the recorded VM; full CLI checklist/report still pending |
| Hyprland | Baseline and return sessions validated in the recorded VM; CLI report still pending |
| GNOME, Xfce, Cinnamon, COSMIC | Awaiting integration testing |
| LXQt, MATE, Budgie, Deepin, LXDE, Enlightenment | Awaiting integration testing |
| Sway, Niri, i3, Openbox | Compositor/window-manager candidates; awaiting integration testing |

These are research targets, not compatibility claims, a popularity ranking or an
exhaustive inventory of Linux desktops. Additional candidates are welcome with
reports. Lack of verification does not mean a desktop is incompatible.

The owner's Plasma + Omarchy shell experience motivates KDE testing first. It
is not evidence that every shell feature works on arbitrary Omarchy versions.
No private machine configuration is included in this repository.

## Shell enabled by default

Every qualifying setup must run Omarchy shell by default with its configuration
preserved. Disabling it is a later explicit user choice, never an installation
workaround. Verify startup and service coexistence without duplicate instances.

## Promotion to tested

Use [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) on a disposable graphical VM or
dedicated test machine. Complete all required checks with evidence and exact
versions. Report modifications and native replacements honestly. Review the
report, then register its repository path under `(desktop, exact Omarchy
version)` in `omarchy_desktop/compatibility.py`. Never add an entry based on unit
tests, a process listing or an unsupported claim from an AI.

The installed version must match exactly to qualify. The report's other version,
hardware and configuration constraints must also be checked by the receiving
agent before planning changes. Upgrades invalidate the assumption of continued
compatibility and require retesting. A reviewed report does not bypass approval.

## Research references

- [Upstream shell architecture](https://github.com/omacom/omarchy/blob/quattro/docs/omarchy-shell.md)
- [A KDE-based NixOS port](https://github.com/fandangos/nixos-omarchy-kde) describes
  Omarchy shell on Plasma. It is a different OS/configuration and does not certify
  a stock Omarchy installation or other desktops.

Neither source substitutes for this project's integration test reports.

## Reported regression to reproduce

On the owner's actual computer, returning to KDE reportedly showed SDDM login,
then an identical-looking login screen, then the desktop. The same password
worked on both screens. Cause is unconfirmed;
this has not yet been reproduced in the test VM. Correlate session/SDDM logs to
distinguish a failed first session, a second greeter and a lock screen. Do not
disable authentication or locking as a workaround. Require one intended login
and verify explicit/idle locking still works.
