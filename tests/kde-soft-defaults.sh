#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -euo pipefail

readonly project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly work_dir=$(mktemp -d "$project_dir/tests/.kde-soft-defaults.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT

run_defaults() {
  env \
    HOME="$1/home" \
    XDG_CONFIG_HOME="$1/home/.config" \
    XDG_STATE_HOME="$1/home/.local/state" \
    XDG_DATA_HOME="$1/data" \
    XDG_CURRENT_DESKTOP="${2:-}" \
    PATH="$work_dir/bin:/usr/bin" \
    "$project_dir/src/bin/frankenstein-kde-soft-defaults" "$3"
}

mkdir -p \
  "$work_dir/bin" \
  "$work_dir/fresh/home/.config/autostart" \
  "$work_dir/fresh/data/color-schemes" \
  "$work_dir/fresh/data/icons/whiteglass/cursors" \
  "$work_dir/fresh/data/frankenstein/presets" \
  "$work_dir/fresh/data/wallpapers/FrankensteinDusk/contents/images"
cp "$project_dir/src/frankenstein/themes/dusk/FrankensteinDusk.colors" \
  "$work_dir/fresh/data/color-schemes/"
cp "$project_dir/src/sddm/frankenstein/backgrounds/vaporwave-default.png" \
  "$work_dir/fresh/data/wallpapers/FrankensteinDusk/contents/images/1672x941.png"
printf 'fixture XCursor data\n' \
  >"$work_dir/fresh/data/icons/whiteglass/cursors/left_ptr"
cp "$project_dir/src/frankenstein/presets/dusk-9x.json" \
  "$work_dir/fresh/data/frankenstein/presets/"
cat >"$work_dir/bin/plasma-apply-wallpaperimage" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$1" >>"$XDG_STATE_HOME/wallpaper-calls"
mkdir -p "$XDG_CONFIG_HOME"
printf '[Containments][1][Wallpaper]\nwallpaperplugin=org.kde.image\nImage=%s\n' "$1" \
  >"$XDG_CONFIG_HOME/plasma-org.kde.plasma.desktop-appletsrc"
EOF
cat >"$work_dir/bin/plasma-apply-colorscheme" <<'EOF'
#!/usr/bin/env bash
kwriteconfig6 --file "$XDG_CONFIG_HOME/kdeglobals" \
  --group General --key ColorScheme "$1"
EOF
chmod 0755 \
  "$work_dir/bin/plasma-apply-colorscheme" \
  "$work_dir/bin/plasma-apply-wallpaperimage"

run_defaults "$work_dir/fresh" "" apply
fresh_state=$work_dir/fresh/home/.local/state/frankenstein/kde-soft-defaults-v1
grep -q '^color=applied$' "$fresh_state"
grep -q '^style=applied$' "$fresh_state"
grep -q '^icons=unavailable$' "$fresh_state"
grep -q '^cursor=applied$' "$fresh_state"
grep -q '^wallpaper=pending$' "$fresh_state"
[[ $(kreadconfig6 --file "$work_dir/fresh/home/.config/kdeglobals" \
  --group General --key ColorScheme) == FrankensteinDusk ]]
[[ $(kreadconfig6 --file "$work_dir/fresh/home/.config/kdeglobals" \
  --group KDE --key widgetStyle) == Windows ]]
[[ $(kreadconfig6 --file "$work_dir/fresh/home/.config/kcminputrc" \
  --group Mouse --key cursorTheme) == whiteglass ]]

touch "$work_dir/fresh/home/.config/autostart/frankenstein-kde-soft-defaults.desktop"
run_defaults "$work_dir/fresh" KDE login
grep -q '^wallpaper=applied$' "$fresh_state"
[[ ! -e $work_dir/fresh/home/.config/autostart/frankenstein-kde-soft-defaults.desktop ]]
[[ $(wc -l <"$work_dir/fresh/home/.local/state/wallpaper-calls") == 1 ]]

kwriteconfig6 --file "$work_dir/fresh/home/.config/kdeglobals" \
  --group KDE --key widgetStyle Breeze
run_defaults "$work_dir/fresh" KDE apply
[[ $(kreadconfig6 --file "$work_dir/fresh/home/.config/kdeglobals" \
  --group KDE --key widgetStyle) == Breeze ]]
[[ $(wc -l <"$work_dir/fresh/home/.local/state/wallpaper-calls") == 1 ]]

mkdir -p \
  "$work_dir/existing/home/.config" \
  "$work_dir/existing/data/color-schemes" \
  "$work_dir/existing/data/wallpapers/FrankensteinDusk/contents/images"
cp -a "$work_dir/fresh/data/." "$work_dir/existing/data/"
cat >"$work_dir/existing/home/.config/kdeglobals" <<'EOF'
[General]
ColorScheme=Existing
[KDE]
widgetStyle=Breeze
[Icons]
Theme=ExistingIcons
EOF
cat >"$work_dir/existing/home/.config/kcminputrc" <<'EOF'
[Mouse]
cursorTheme=ExistingCursor
EOF
cat >"$work_dir/existing/home/.config/plasma-org.kde.plasma.desktop-appletsrc" <<'EOF'
[Containments][1][Wallpaper]
wallpaperplugin=org.kde.image
Image=file:///existing.png
EOF
existing_before=$(sha256sum "$work_dir/existing/home/.config/"* | sha256sum)
run_defaults "$work_dir/existing" KDE apply
existing_after=$(sha256sum "$work_dir/existing/home/.config/"* | sha256sum)
[[ $existing_before == "$existing_after" ]]
existing_state=$work_dir/existing/home/.local/state/frankenstein/kde-soft-defaults-v1
grep -q '^color=preserved$' "$existing_state"
grep -q '^style=preserved$' "$existing_state"
grep -q '^icons=preserved$' "$existing_state"
grep -q '^cursor=preserved$' "$existing_state"
grep -q '^wallpaper=preserved$' "$existing_state"

for case in missing invalid; do
  mkdir -p \
    "$work_dir/$case/home/.config/autostart" \
    "$work_dir/$case/home/.local/state/frankenstein" \
    "$work_dir/$case/data/frankenstein/presets"
  cat >"$work_dir/$case/home/.local/state/frankenstein/kde-soft-defaults-v1" <<'EOF'
version=1
color=preserved
style=preserved
icons=preserved
cursor=preserved
wallpaper=pending
EOF
  touch "$work_dir/$case/home/.config/autostart/frankenstein-kde-soft-defaults.desktop"
  if [[ $case == invalid ]]; then
    printf '{}\n' >"$work_dir/$case/data/frankenstein/presets/dusk-9x.json"
  fi
  run_defaults "$work_dir/$case" KDE login
  grep -q '^wallpaper=unavailable$' \
    "$work_dir/$case/home/.local/state/frankenstein/kde-soft-defaults-v1"
  [[ ! -e $work_dir/$case/home/.config/autostart/frankenstein-kde-soft-defaults.desktop ]]
  [[ ! -e $work_dir/$case/home/.config/plasma-org.kde.plasma.desktop-appletsrc ]]
done

echo "KDE soft-default tests passed"
