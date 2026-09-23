#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -euo pipefail

readonly repository_mount=/mnt/frankenstein-repository
readonly results_mount=/mnt/frankenstein-results
readonly installed_repository=/var/lib/frankenstein-test-repository
readonly pacman_include=/etc/pacman.d/frankenstein-test.conf
readonly pacman_backup=/etc/pacman.conf.frankenstein-test-backup
readonly source_root=${FRANKENSTEIN_TEST_REPOSITORY_SOURCE:-$repository_mount}

usage() {
  echo "Usage: ${0##*/} <install|update|cleanup> <full-key-fingerprint>" >&2
  exit 2
}

[[ $EUID -eq 0 && $# == 2 ]] || usage
action=$1
fingerprint=${2^^}
[[ $fingerprint =~ ^[[:xdigit:]]{40}$ ]] || usage

mount_if_needed() {
  local device=$1 target=$2 options=${3:-}
  mkdir -p "$target"
  if ! mountpoint -q "$target"; then
    if [[ -n $options ]]; then
      mount -o "$options" "$device" "$target"
    else
      mount "$device" "$target"
    fi
  fi
}

verify_public_key() {
  local actual
  actual=$(gpg --batch --show-keys --with-colons \
    "$repository_mount/frankenstein-repository.asc" |
    awk -F: '$1 == "fpr" { print toupper($10); exit }')
  [[ $actual == "$fingerprint" ]] || {
    echo "Repository key fingerprint mismatch: $actual" >&2
    exit 1
  }
}

publish_snapshot() {
  local snapshot=$1
  local staging=$installed_repository.new
  rm -rf "$staging"
  mkdir -p "$staging"
  cp -a "$source_root/$snapshot/x86_64/." "$staging/"
  rm -rf "$installed_repository"
  mv "$staging" "$installed_repository"
}

mount_if_needed /dev/vdb "$repository_mount" ro
mount_if_needed /dev/vdc "$results_mount"
exec > >(tee "$results_mount/repository-$action.log") 2>&1

case $action in
  install)
    [[ ! -e $pacman_backup ]] || {
      echo "The repository test is already initialized." >&2
      exit 1
    }
    verify_public_key
    pacman-key --add "$repository_mount/frankenstein-repository.asc"
    pacman-key --lsign-key "$fingerprint"
    pacman-key --finger "$fingerprint"

    publish_snapshot v1
    cp -a /etc/pacman.conf "$pacman_backup"
    cat >"$pacman_include" <<'EOF'
[frankenstein]
SigLevel = Required DatabaseRequired
Server = file:///var/lib/frankenstein-test-repository
EOF
    printf '\nInclude = %s\n' "$pacman_include" >>/etc/pacman.conf

    pacman --sync --refresh --noconfirm
    pacman --sync --noconfirm frankenstein-core frankenstein-kde
    pacman -Q frankenstein-core frankenstein-kde \
      | tee "$results_mount/repository-install-versions.log"
    ;;
  update)
    verify_public_key
    publish_snapshot v2
    env OMARCHY_ALLOW_DIRECT_PACMAN=1 \
      pacman --sync --refresh --sysupgrade --noconfirm
    pacman -Q frankenstein-core frankenstein-kde \
      | tee "$results_mount/repository-update-versions.log"
    ;;
  cleanup)
    [[ -f $pacman_backup ]] && mv -f "$pacman_backup" /etc/pacman.conf
    rm -f "$pacman_include"
    rm -rf "$installed_repository"
    pacman-key --delete "$fingerprint" >/dev/null 2>&1 || true
    ;;
  *)
    usage
    ;;
esac
