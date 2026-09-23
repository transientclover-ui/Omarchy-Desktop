#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -euo pipefail

usage() {
  echo "Usage: ${0##*/} <isolated-gnupg-directory>" >&2
  exit 2
}

[[ $# == 1 ]] || usage

key_home=$(realpath -m -- "$1")
[[ ! -e $key_home ]] || {
  echo "Refusing to reuse an existing test-key directory: $key_home" >&2
  exit 1
}

umask 077
mkdir -p "$key_home"
export GNUPGHOME=$key_home

gpg --batch --pinentry-mode loopback --passphrase '' \
  --quick-generate-key \
  'Frankenstein VM Test Repository <vm-test@frankenstein.invalid>' \
  ed25519 sign 30d

fingerprint=$(gpg --batch --with-colons --list-secret-keys |
  awk -F: '$1 == "fpr" { print $10; exit }')
[[ $fingerprint =~ ^[[:xdigit:]]{40}$ ]] || {
  echo "Could not determine the generated signing-key fingerprint." >&2
  exit 1
}

printf '%s\n' "$fingerprint"
