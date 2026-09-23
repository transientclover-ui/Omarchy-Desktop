# Omarchy shell compatibility

This project aims to offer every widely used desktop **once a specific
combination has passed Omarchy shell integration tests**. Installing a desktop
on Arch Linux is not the same as preserving the Omarchy shell experience.

## Current evidence

There are currently **no project-verified combinations**. The original CLI tests
validate this tool, not graphical desktop compatibility. Therefore install and
switch requests now produce inspection-only prompts until a version-matched
compatibility report is registered. Recovery and SDDM diagnosis remain available.

| Candidates | Current status |
| --- | --- |
| KDE Plasma | Awaiting full integration test report |
| Hyprland | Omarchy's baseline desktop; awaiting this project's versioned test report |
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
