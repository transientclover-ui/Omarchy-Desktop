#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -euo pipefail

usage() {
  cat >&2 <<'EOF'
Usage: build.sh --key <fingerprint> --output <directory> <package>...

GNUPGHOME must name an explicit isolated keyring containing the signing key.
The output directory must not already exist.
EOF
  exit 2
}

key=
output=
while (($#)); do
  case $1 in
    --key)
      shift
      key=${1:-}
      ;;
    --output)
      shift
      output=${1:-}
      ;;
    --help|-h)
      usage
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown argument: $1" >&2
      usage
      ;;
    *)
      break
      ;;
  esac
  shift
done

[[ -n $key && -n $output && $# -gt 0 ]] || usage
[[ -n ${GNUPGHOME:-} && -d $GNUPGHOME ]] || {
  echo "GNUPGHOME must identify an existing isolated keyring." >&2
  exit 1
}
[[ $key =~ ^[[:xdigit:]]{40}$ ]] || {
  echo "Use the signing key's full 40-character fingerprint." >&2
  exit 1
}
gpg --batch --list-secret-keys "$key" >/dev/null 2>&1 || {
  echo "The requested secret signing key is unavailable in GNUPGHOME." >&2
  exit 1
}

output=$(realpath -m -- "$output")
[[ ! -e $output ]] || {
  echo "Refusing to replace an existing repository: $output" >&2
  exit 1
}

repo_dir=$output/x86_64
mkdir -p "$repo_dir"

packages=()
for source_package in "$@"; do
  [[ -f $source_package && $source_package == *.pkg.tar.zst ]] || {
    echo "Not an Arch package: $source_package" >&2
    exit 1
  }
  destination=$repo_dir/${source_package##*/}
  cp -- "$source_package" "$destination"
  gpg --batch --yes --local-user "$key" --detach-sign "$destination"
  packages+=("$destination")
done

repo-add --quiet --sign --key "$key" --include-sigs \
  "$repo_dir/frankenstein.db.tar.gz" "${packages[@]}"
gpg --batch --armor --export "$key" >"$output/frankenstein-repository.asc"
printf '%s\n' "$key" >"$output/SIGNING-KEY-FINGERPRINT"
(
  cd "$output"
  find . -type f ! -name SHA256SUMS -print0 |
    LC_ALL=C sort -z |
    xargs -0 sha256sum >SHA256SUMS
)

echo "Signed repository created at $output"
