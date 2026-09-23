# Frankenstein

Frankenstein adds a reversible KDE Plasma compatibility profile to an existing
Omarchy installation while preserving the original Omarchy/Hyprland session.

The verified implementation currently includes:

- an SDDM session chooser and independent Breeze-derived theme
- persistent default-desktop selection with one-time SDDM overrides
- an Omarchy menu extension for desktop selection
- a KDE-specific filtered Omarchy Shell profile
- native KDE adapters for desktop settings and terminal actions

Only KDE Plasma is supported in this checkpoint. See
[`COMPATIBILITY-JOURNAL.md`](COMPATIBILITY-JOURNAL.md) for verification evidence,
known limitations, and rollback instructions.

See [`DISTRIBUTION.md`](DISTRIBUTION.md) for isolated signing-key handling,
repository creation, and the public-key trust procedure.
