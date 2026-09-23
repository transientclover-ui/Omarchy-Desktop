# Third-party notices

## Omarchy

The following files are modified copies of Omarchy 4.0.4:

- `src/frankenstein/omarchy-shell/shell.qml`
- `src/frankenstein/omarchy-shell/services/PluginRegistry.qml`
- `src/frankenstein/omarchy-shell/plugins/menu/Menu.qml`

Upstream project: <https://github.com/basecamp/omarchy>

Upstream copyright:

> Copyright (c) David Heinemeier Hansson

Omarchy is distributed under the MIT License. The applicable text is retained
in `LICENSES/MIT.txt`.

Frankenstein modifications:

- suppress the Omarchy bar for desktop profiles that retain their native panel
- filter effective shell plugins through a desktop-specific allowlist
- redirect the Omarchy menu entry point to a compatibility-owned copy
- load a desktop-profile menu overlay after the user's existing menu extension
- report effective profile state through shell IPC

## Breeze

Frankenstein does not bundle or modify the Breeze SDDM theme. Its original
MIT-licensed SDDM configuration selects the separately installed `breeze`
package. The unused Breeze-derived prototype metadata was removed before the
release-candidate distribution build.

## Runtime dependencies

Frankenstein invokes but does not bundle:

- Omarchy (MIT)
- Quickshell (LGPL-3.0-only)
- KDE Plasma, Breeze, and System Settings (LGPL-2.0-or-later)
- SDDM (GPL-2.0-or-later)

Those projects remain under their respective licenses. Their package metadata
and installed license files are authoritative for the versions installed by
the user.
