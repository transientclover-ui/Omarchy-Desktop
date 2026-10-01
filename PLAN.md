# Frankenstein v1 release-candidate boundary

## Included

- read-only session, SDDM, ownership, compatibility, and state diagnostics
- KDE Plasma Wayland and Omarchy/Hyprland coexistence without wrapping Plasma
  in UWSM
- preserved-shell and explicit filtered-adapter paths
- approved, backed-up, reversible installation and recovery
- explicit default-session switching
- Frankenstein SDDM theme with a prominent session selector
- bundled vaporwave fallback and staged local-image workflow
- documented non-sensitive agent-readable state
- fixture-contained validation; no automated live display-manager mutation

## Deliberately excluded

- removing desktops or shared dependencies
- speculative PAM, keyring, service, or session resets
- arbitrary filesystem browsing from the unauthenticated greeter
- automatic SDDM restart, logout, or reboot
- migration based solely on uncertain ownership
- unsupported desktop-specific management beyond reporting detected sessions
- GitHub Release or OmaStore publication
- a display power-cycle workaround without a verified recovery action

## Release-candidate exit checks

The candidate is complete only when the full fixture suite, shell/static
checks, clean package build, package-content checks, installed-command check,
theme validation, state validation, and artifact privacy scan pass; the
development journal records exact results; one local checkpoint commit exists;
and the tracked working tree is clean.

Future work belongs here only if it is required to correct a concrete v1
defect. Optional integrations and publication remain post-v1 tasks.
