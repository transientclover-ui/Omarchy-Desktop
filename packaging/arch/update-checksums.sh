#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -euo pipefail

readonly script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

startdir=$script_dir
# shellcheck disable=SC1091
source "$script_dir/PKGBUILD"
for source_spec in "${source[@]}"; do
  source_name=${source_spec%%::*}
  [[ $source_name == "$source_spec" ]] && source_name=${source_spec##*/}
  rm -f -- "$script_dir/$source_name"
done

cd "$script_dir"
updpkgsums PKGBUILD
makepkg --printsrcinfo >.SRCINFO
