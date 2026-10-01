#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -euo pipefail

readonly script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly reboot_required_marker=/run/reboot-required
readonly modules_dir=/usr/lib/modules
readonly update_restart_guard=$script_dir/src/update-safety-bin/omarchy-update-restart

usage() {
  cat >&2 <<'EOF'
Usage: ./install-frankenstein.sh CORE_PACKAGE KDE_PACKAGE [-- SETUP_OPTIONS...]

Runs the supported Omarchy full-system update first, stops if a reboot is
advisable, installs the two matching Frankenstein packages, then runs
Frankenstein setup. It never reboots or restarts SDDM.
EOF
  exit 2
}

[[ $EUID -ne 0 ]] || {
  echo "Run this installer as the target desktop user, not as root." >&2
  exit 1
}
[[ $# -ge 2 ]] || usage

core_package=$1
kde_package=$2
shift 2
if [[ ${1:-} == -- ]]; then
  shift
elif (($#)); then
  usage
fi

for command_name in omarchy pacman sudo frankenstein uname; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "Required installation command is missing: $command_name" >&2
    exit 1
  }
done
for package in "$core_package" "$kde_package"; do
  [[ -f $package && ! -L $package && -r $package ]] || {
    echo "Package is missing, linked, or unreadable: $package" >&2
    exit 1
  }
done
[[ -x $update_restart_guard ]] || {
  echo "Update restart-safety helper is missing: $update_restart_guard" >&2
  exit 1
}

core_name=$(pacman -Qp -- "$core_package" | awk '{print $1}')
kde_name=$(pacman -Qp -- "$kde_package" | awk '{print $1}')
[[ $core_name == frankenstein-core && $kde_name == frankenstein-kde ]] || {
  echo "Expected frankenstein-core followed by frankenstein-kde packages." >&2
  exit 1
}

echo "Updating Omarchy and all system packages before Frankenstein installation..."
update_advisory=$(mktemp)
rm -f "$update_advisory"
cleanup() {
  rm -f "$update_advisory"
}
trap cleanup EXIT
if env \
  PATH="$script_dir/src/update-safety-bin:$PATH" \
  FRANKENSTEIN_UPDATE_ADVISORY="$update_advisory" \
  omarchy update -y; then
  :
else
  status=$?
  echo "System update failed; Frankenstein packages and configuration were not installed." >&2
  exit "$status"
fi

running_kernel=$(uname -r)
if [[ -e $update_advisory || -e $reboot_required_marker ||
      ! -d $modules_dir/$running_kernel ]]; then
  cat >&2 <<EOF
The system update completed, but a reboot is advisable before Frankenstein
installation. Frankenstein packages and desktop configuration were not changed.
Reboot normally, then rerun this command.
EOF
  exit 75
fi

echo "System update completed without a detected reboot boundary."
sudo pacman -U --needed -- "$core_package" "$kde_package"
frankenstein install "$@"
