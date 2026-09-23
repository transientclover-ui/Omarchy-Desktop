#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -euo pipefail

readonly script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly repository_root=$(cd -- "$script_dir/../.." && pwd)

export SOURCE_DATE_EPOCH
SOURCE_DATE_EPOCH=$(git -C "$repository_root" log -1 --format=%ct)

cd "$script_dir"
exec makepkg --config "$script_dir/makepkg.conf" "$@"
