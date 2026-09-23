#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
sha256sum -c omarchy-4.0.4.iso.sha256
exec qemu-system-x86_64 \
  -name 'Omarchy desktop compatibility lab' \
  -machine q35,accel=kvm -cpu host -smp 4 -m 4096 \
  -drive if=pflash,format=raw,readonly=on,file=/usr/share/edk2/x64/OVMF_CODE.4m.fd \
  -drive if=pflash,format=raw,file=OVMF_VARS.fd \
  -drive file=omarchy-kde-after-baseline.qcow2,format=qcow2,if=none,id=drive0 \
  -device virtio-blk-pci,drive=drive0,bootindex=1 \
  -drive file=omarchy-4.0.4.iso,media=cdrom,if=none,format=raw,id=cdrom0 \
  -device ide-cd,drive=cdrom0,bootindex=2 \
  -device virtio-vga -display gtk \
  -usb -device usb-tablet \
  -netdev user,id=net0 -device virtio-net-pci,netdev=net0 \
  -qmp unix:control.sock,server=on,wait=off \
  -serial file:serial.log -boot menu=on
