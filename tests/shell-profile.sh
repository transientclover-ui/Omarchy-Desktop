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

effective=$(frankenstein_effective_shell_profile "$base")
assert_equal native "$(jq -r '.shell.panel' <<<"$effective")" "safe default panel"
assert_equal omarchy.menu \
  "$(jq -r '.shell.enabledPlugins | join(\",\")' <<<"$effective")" \
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
  "$(jq -r '.shell.enabledPlugins | join(\",\")' <<<"$effective")" \
  "custom plugin allowlist"
assert_equal KDE "$(jq -r '.desktop' <<<"$effective")" "base desktop preservation"

cat >"$work_dir/invalid.json" <<'EOF'
{
  "schemaVersion": 1,
  "desktop": "Hyprland",
  "shell": {
    "enabledPlugins": ["omarchy.menu", "omarchy.menu"]
  }
}
EOF
if frankenstein_validate_shell_profile_override "$work_dir/invalid.json" 2>/dev/null; then
  fail "invalid profile override was accepted"
fi

cat >"$work_dir/invalid-id.json" <<'EOF'
{
  "schemaVersion": 1,
  "shell": {
    "enabledPlugins": ["unsafe,plugin"]
  }
}
EOF
if frankenstein_validate_shell_profile_override "$work_dir/invalid-id.json" 2>/dev/null; then
  fail "unsafe plugin identifier was accepted"
fi

echo "shell profile regression tests passed"
