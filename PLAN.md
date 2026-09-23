# Project plan

## Version 0.1 scope

1. Standard-library Python CLI with a guided chooser and explicit subcommands.
2. Read-only session/SDDM discovery with source paths and honest uncertainty.
3. Agent-independent inspect, install, switch and recovery prompts.
4. SDDM diagnosis/repair prompts, especially the last-used-session symptom.
5. Temporary-fixture tests, packaging, CI, MIT license and beginner documentation.
6. Prepare a local Git repository; publish only with the owner's explicit approval.

## Future work requiring separate validation

- Disposable VM compatibility tests for named Omarchy/SDDM releases.
- More complete desktop-entry escaping and alternate display-manager adapters.
- Opt-in, privacy-reviewed runtime diagnostics with narrowly allowlisted readers.
- Documentation translations and accessibility feedback for the menu.

An automatic installer, automatic login repair, AI execution, package removal,
service disabling and live-session switching are outside version 0.1 scope.

## Version 0.2: shell compatibility first

Broaden the candidate catalog, distinguish evidence from session presence, require
reviewed version-matched graphical reports before install/switch prompts, and
keep Omarchy shell enabled by default. Add a compatibility status command and a
verification-planning prompt. Actual multi-desktop graphical testing remains
outstanding and must use disposable systems; no combinations are certified yet.
