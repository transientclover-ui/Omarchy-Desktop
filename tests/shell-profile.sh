#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -euo pipefail

readonly project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly work_dir=$(mktemp -d "$project_dir/tests/.shell-profile.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT

# shellcheck source=src/lib/shell-profile.sh
source "$project_dir/src/lib/shell-profile.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_equal() {
  local expected=$1 actual=$2 description=$3
  [[ $actual == "$expected" ]] ||
    fail "$description: expected '$expected', got '$actual'"
}

base=$project_dir/src/frankenstein/plasma-shell-profile.json

base_before=$(sha256sum "$base")
effective=$(frankenstein_effective_shell_profile "$base")
assert_equal native "$(jq -r '.shell.panel' <<<"$effective")" "safe default panel"
assert_equal omarchy.menu \
  "$(jq -r '.shell.enabledPlugins | join(",")' <<<"$effective")" \
  "safe default plugin allowlist"

cat >"$work_dir/custom.json" <<'EOF'
{
  "schemaVersion": 1,
  "shell": {
    "panel": "omarchy",
    "enabledPlugins": [
      "omarchy.menu",
      "omarchy.clock",
      "terminal.tetris"
    ]
  }
}
EOF
effective=$(frankenstein_effective_shell_profile "$base" "$work_dir/custom.json")
assert_equal omarchy "$(jq -r '.shell.panel' <<<"$effective")" "custom panel"
assert_equal omarchy.menu,omarchy.clock,terminal.tetris \
  "$(jq -r '.shell.enabledPlugins | join(",")' <<<"$effective")" \
  "custom plugin allowlist"
assert_equal KDE "$(jq -r '.desktop' <<<"$effective")" "base desktop preservation"

# A missing override must preserve the complete packaged profile.
effective=$(frankenstein_effective_shell_profile "$base" "$work_dir/missing.json")
assert_equal "$(cat "$base")" "$effective" "missing override fallback"

# Each optional field can be overridden independently; arrays replace defaults.
printf '%s\n' '{"schemaVersion":1,"shell":{"panel":"omarchy"}}' >"$work_dir/panel.json"
effective=$(frankenstein_effective_shell_profile "$base" "$work_dir/panel.json")
expected=$(jq -cS '.shell.panel = "omarchy"' "$base")
assert_equal "$expected" "$(jq -cS . <<<"$effective")" "panel-only merge"

printf '%s\n' '{"schemaVersion":1,"shell":{"enabledPlugins":[]}}' >"$work_dir/plugins.json"
effective=$(frankenstein_effective_shell_profile "$base" "$work_dir/plugins.json")
expected=$(jq -cS '.shell.enabledPlugins = []' "$base")
assert_equal "$expected" "$(jq -cS . <<<"$effective")" "empty plugin list replaces defaults"

printf '%s\n' '{"schemaVersion":1,"shell":{"enabledPlugins":["terminal.tetris"]}}' >"$work_dir/plugins.json"
override_before=$(sha256sum "$work_dir/plugins.json")
effective=$(frankenstein_effective_shell_profile "$base" "$work_dir/plugins.json")
expected=$(jq -cS '.shell.enabledPlugins = ["terminal.tetris"]' "$base")
assert_equal "$expected" "$(jq -cS . <<<"$effective")" "plugin-only merge preserves other fields"
assert_equal "$override_before" "$(sha256sum "$work_dir/plugins.json")" "override remains unchanged"

# Isolate invalid fields so one rejection cannot hide a different validation bug.
invalid_count=0
while IFS= read -r invalid; do
  invalid_count=$((invalid_count + 1))
  printf '%s\n' "$invalid" >"$work_dir/invalid.json"
  if frankenstein_validate_shell_profile_override "$work_dir/invalid.json" 2>/dev/null; then
    fail "invalid override $invalid_count was accepted: $invalid"
  fi
  if frankenstein_effective_shell_profile "$base" "$work_dir/invalid.json" \
      >"$work_dir/rejected-output" 2>/dev/null; then
    fail "merge accepted invalid override $invalid_count"
  fi
  [[ ! -s $work_dir/rejected-output ]] || fail "invalid override emitted an effective profile"
done <<'EOF'
{
null
[]
{}
{"schemaVersion":2,"shell":{"panel":"native"}}
{"schemaVersion":"1","shell":{"panel":"native"}}
{"shell":{"panel":"native"}}
{"schemaVersion":1}
{"schemaVersion":1,"shell":null}
{"schemaVersion":1,"shell":[]}
{"schemaVersion":1,"shell":{}}
{"schemaVersion":1,"desktop":"Hyprland","shell":{"panel":"native"}}
{"schemaVersion":1,"shell":{"panel":"native","unknown":true}}
{"schemaVersion":1,"shell":{"panel":"unknown"}}
{"schemaVersion":1,"shell":{"panel":null}}
{"schemaVersion":1,"shell":{"enabledPlugins":null}}
{"schemaVersion":1,"shell":{"enabledPlugins":"omarchy.menu"}}
{"schemaVersion":1,"shell":{"enabledPlugins":[1]}}
{"schemaVersion":1,"shell":{"enabledPlugins":[""]}}
{"schemaVersion":1,"shell":{"enabledPlugins":["unsafe,plugin"]}}
{"schemaVersion":1,"shell":{"enabledPlugins":["plugin with spaces"]}}
{"schemaVersion":1,"shell":{"enabledPlugins":["omarchy.menu","omarchy.menu"]}}
EOF

# A valid override cannot rescue an invalid packaged profile.
jq '.shell.panel = "unknown"' "$base" >"$work_dir/invalid-base.json"
if frankenstein_effective_shell_profile "$work_dir/invalid-base.json" "$work_dir/panel.json" \
    >"$work_dir/rejected-output" 2>/dev/null; then
  fail "invalid packaged profile was accepted"
fi
[[ ! -s $work_dir/rejected-output ]] || fail "invalid base emitted an effective profile"
assert_equal "$base_before" "$(sha256sum "$base")" "packaged profile remains unchanged"

echo "shell profile regression tests passed ($invalid_count invalid override cases)"
