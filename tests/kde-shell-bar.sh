#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -euo pipefail

readonly project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly work_dir=$(mktemp -d "$project_dir/tests/.kde-shell-bar.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT

source_bar=/usr/share/omarchy/shell/plugins/bar/Bar.qml
generated_bar=$work_dir/Bar.qml
profile=$project_dir/src/frankenstein/plasma-shell-profile.json

"$project_dir/src/libexec/frankenstein-kde-bar-compat" "$source_bar" "$generated_bar"

! grep -qE 'Quickshell\.Hyprland|Hyprland\.focusedMonitor' "$generated_bar"
grep -q 'function focusedScreenName()' "$generated_bar"
grep -q 'return ""' "$generated_bar"
grep -q 'PanelWindow' "$generated_bar"

[[ $(jq -r '.shell.panel' "$profile") == native ]]
[[ $(jq -r '.shell.enabledPlugins | length' "$profile") == 0 ]]
[[ $(jq -r '.plasmaPanel' \
  "$project_dir/src/frankenstein/presets/dusk-9x.json") == native ]]
[[ $(jq -r '.omarchyBar' \
  "$project_dir/src/frankenstein/presets/dusk-9x.json") == soft-default ]]
grep -q 'shell_profile_default=omarchy' "$project_dir/install.sh"

grep -q 'compatibilityAllowlist === "__none__" && manifest.__isFirstParty' \
  "$project_dir/src/frankenstein/omarchy-shell/services/PluginRegistry.qml"
grep -q 'OnlyShowIn=KDE;' \
  "$project_dir/src/frankenstein/frankenstein-omarchy-shell-autostart.desktop"
grep -q 'PartOf=plasma-workspace.target' \
  "$project_dir/src/systemd/frankenstein-omarchy-shell.service"

scheme=$project_dir/src/frankenstein/themes/dusk/FrankensteinDusk.colors
grep -q '^Name=Frankenstein Dusk$' "$scheme"
grep -q '^BackgroundNormal=24,22,36$' "$scheme"
grep -q '^ForegroundNormal=215,207,226$' "$scheme"
! grep -Eq 'kwriteconfig|plasma-apply-(color|lookandfeel)' "$project_dir/install.sh"
! grep -q 'FRANKENSTEIN_SHELL_THEME' \
  "$project_dir/src/bin/frankenstein-shell-adapter"

echo "KDE Omarchy bar compatibility tests passed"
