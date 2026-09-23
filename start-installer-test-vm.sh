#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -euo pipefail

readonly project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly baseline=$project_dir/omarchy-kde.qcow2
readonly overlay=$project_dir/omarchy-frankenstein-installer-test.qcow2
readonly payload=$project_dir/frankenstein-installer-payload.img
readonly results=$project_dir/frankenstein-installer-results.img
readonly variables=$project_dir/OVMF_VARS-installer-test.fd
readonly socket=installer-test-control.sock

cd "$project_dir"

for required_file in "$baseline" "$overlay" "$payload" "$results"; do
  [[ -f $required_file ]] || {
    echo "Missing VM test file: $required_file" >&2
    exit 1
  }
done

backing=$(qemu-img info --output=json "$overlay" | jq -r '."full-backing-filename" // ."backing-filename" // empty')
[[ $(readlink -f -- "$backing") == "$(readlink -f -- "$baseline")" ]] || {
  echo "Refusing to boot an overlay not backed by the preserved baseline." >&2
  exit 1
}

if [[ -S $socket ]]; then
  if python - "$socket" <<'PY'
import socket
import sys

connection = socket.socket(socket.AF_UNIX)
connection.settimeout(0.2)
try:
    connection.connect(sys.argv[1])
except OSError:
    raise SystemExit(1)
else:
    raise SystemExit(0)
PY
  then
    echo "The installer-test VM control socket is active." >&2
    exit 1
  fi
  rm -f -- "$socket"
fi

if [[ ! -f $variables ]]; then
  cp /usr/share/edk2/x64/OVMF_VARS.4m.fd "$variables"
fi

exec qemu-system-x86_64 \
  -name 'Frankenstein fresh-install test' \
  -machine q35,accel=kvm -cpu host -smp 4 -m 4096 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/x64/OVMF_CODE.4m.fd \
  -drive if=pflash,format=raw,file="$variables" \
  -drive file="$overlay",format=qcow2,if=none,id=system \
  -device virtio-blk-pci,drive=system,bootindex=1 \
  -drive file="$payload",format=raw,if=none,id=payload,readonly=on \
  -device virtio-blk-pci,drive=payload \
  -drive file="$results",format=raw,if=none,id=results \
  -device virtio-blk-pci,drive=results \
  -device virtio-vga -display gtk \
  -usb -device usb-tablet \
  -netdev user,id=net0 -device virtio-net-pci,netdev=net0 \
  -qmp unix:"$socket",server=on,wait=off \
  -serial file:installer-test-serial.log \
  -boot c
