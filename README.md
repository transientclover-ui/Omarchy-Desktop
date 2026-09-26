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

The proposed [cross-session shell ownership policy](docs/SHELL-OWNERSHIP.md)
defines the remaining preserved-shell lifecycle work and acceptance cases.
It is a design contract, not an implemented setup option.

[Display Power-Cycle Protection](docs/DISPLAY-POWER-CYCLE.md) records the TV/HDMI
workaround investigation. Integration is deferred pending identification of its
working recovery action; no protection toggle is available yet.

The [KDE Wayland display investigation](docs/DISPLAY-POWER-CYCLE-KDE.md) explains
native reconnect handling and the evidence required before adding a fallback.
