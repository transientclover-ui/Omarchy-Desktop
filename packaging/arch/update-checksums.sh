#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -euo pipefail

readonly script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

startdir=$script_dir
# shellcheck disable=SC1091
source "$script_dir/PKGBUILD"
cleanup() {
  local source_spec source_name
  for source_spec in "${source[@]}"; do
    source_name=${source_spec%%::*}
    [[ $source_name == "$source_spec" ]] && source_name=${source_spec##*/}
    rm -f -- "$script_dir/$source_name"
  done
}
trap cleanup EXIT
for source_spec in "${source[@]}"; do
  source_name=${source_spec%%::*}
  [[ $source_name == "$source_spec" ]] && source_name=${source_spec##*/}
  rm -f -- "$script_dir/$source_name"
done
for source_spec in "${_local_sources[@]}"; do
  source_name=${source_spec%%::*}
  source_path=${source_spec#*::}
  cp -- "$script_dir/$source_path" "$script_dir/$source_name"
done

cd "$script_dir"
updpkgsums PKGBUILD
makepkg --printsrcinfo >.SRCINFO
