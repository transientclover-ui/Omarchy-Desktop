#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -euo pipefail

readonly script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly repository_root=$(cd -- "$script_dir/../.." && pwd)

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
  rm -f -- "$script_dir/$source_name" "$script_dir/sources/$source_name"
done
for source_spec in "${_local_sources[@]}"; do
  source_name=${source_spec%%::*}
  source_path=${source_spec#*::}
  cp -- "$script_dir/$source_path" "$script_dir/$source_name"
done

export SOURCE_DATE_EPOCH
SOURCE_DATE_EPOCH=$(git -C "$repository_root" log -1 --format=%ct)

cd "$script_dir"
makepkg --config "$script_dir/makepkg.conf" "$@"
