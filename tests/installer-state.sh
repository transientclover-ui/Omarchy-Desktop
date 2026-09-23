#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -euo pipefail

readonly project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
readonly work_dir=$(mktemp -d "$project_dir/tests/.installer-state.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT

sudo() {
  "$@"
}

# shellcheck source=src/lib/installer-state.sh
source "$project_dir/src/lib/installer-state.sh"

fail() {
  echo "FAIL: $*" >&2
  exit 1
}

assert_equal() {
  local expected=$1 actual=$2 description=$3
  [[ $actual == "$expected" ]] ||
    fail "$description: expected '$expected', got '$actual'"
}

test_existing_state_restored() {
  local root=$work_dir/existing
  local state=$root/var/lib/sddm/state.conf
  local backup=$root/backup
  mkdir -p "${state%/*}"
  printf '[Last]\nSession=/usr/share/wayland-sessions/plasma.desktop \n' >"$state"
  chmod 0600 "$state"
  touch -t 202601020304.05 "$state"
  local expected_mtime
  expected_mtime=$(stat -c %Y "$state")

  frankenstein_backup_sddm_state "$state" "$backup"
  printf '[Last]\nSession=/usr/local/share/wayland-sessions/omarchy.desktop \n' >"$state"
  chmod 0644 "$state"
  frankenstein_restore_sddm_state "$state" "$backup"

  grep -q 'plasma.desktop' "$state" || fail "existing SDDM state content was not restored"
  assert_equal 600 "$(stat -c %a "$state")" "existing SDDM state mode"
  assert_equal "$expected_mtime" "$(stat -c %Y "$state")" "existing SDDM state mtime"
}

test_absent_state_removed() {
  local root=$work_dir/absent
  local state=$root/var/lib/sddm/state.conf
  local backup=$root/backup
  mkdir -p "${state%/*}"

  frankenstein_backup_sddm_state "$state" "$backup"
  printf '[Last]\nSession=/usr/share/wayland-sessions/plasma.desktop \n' >"$state"
  frankenstein_restore_sddm_state "$state" "$backup"

  [[ ! -e $state ]] || fail "initially absent SDDM state was not removed"
}

test_missing_backup_rejected() {
  local root=$work_dir/missing
  local state=$root/var/lib/sddm/state.conf
  local backup=$root/backup
  mkdir -p "$backup"
  printf 'true\n' >"$backup/sddm-state.existed"

  if frankenstein_restore_sddm_state "$state" "$backup" 2>/dev/null; then
    fail "missing SDDM state backup was accepted"
  fi
}

test_auto_selection() {
  local selected

  selected=$(frankenstein_choose_auto_default \
    KDE plasma '' '' /sessions/omarchy.desktop /sessions/plasma.desktop)
  assert_equal plasma.desktop "$selected" "active Plasma adoption"

  selected=$(frankenstein_choose_auto_default \
    KDE plasma omarchy.desktop '' /sessions/omarchy.desktop /sessions/plasma.desktop)
  assert_equal plasma.desktop "$selected" "active Plasma precedence"

  selected=$(frankenstein_choose_auto_default \
    '' '' plasma.desktop '' /sessions/omarchy.desktop /sessions/plasma.desktop)
  assert_equal plasma.desktop "$selected" "configured Plasma default"

  selected=$(frankenstein_choose_auto_default \
    '' '' '' '/usr/share/wayland-sessions/plasma.desktop ' \
    /sessions/omarchy.desktop /sessions/plasma.desktop)
  assert_equal plasma.desktop "$selected" "remembered Plasma default"

  selected=$(frankenstein_choose_auto_default \
    '' '' '' '' /sessions/omarchy.desktop /sessions/plasma.desktop)
  assert_equal omarchy.desktop "$selected" "Omarchy fallback"
}

test_existing_state_restored
test_absent_state_removed
test_missing_backup_rejected
test_auto_selection

echo "installer state regression tests passed"
