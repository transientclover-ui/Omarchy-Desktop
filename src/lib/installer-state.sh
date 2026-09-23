#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

frankenstein_backup_sddm_state() {
  local state_file=$1 backup_dir=$2 existed=false

  sudo install -d -m 0700 "$backup_dir"
  if sudo test -e "$state_file"; then
    sudo cp -a -- "$state_file" "$backup_dir/sddm-state.conf"
    existed=true
  else
    sudo rm -f "$backup_dir/sddm-state.conf"
  fi
  printf '%s\n' "$existed" |
    sudo tee "$backup_dir/sddm-state.existed" >/dev/null
}

frankenstein_restore_sddm_state() {
  local state_file=$1 backup_dir=$2 existed parent temporary

  existed=$(sudo cat "$backup_dir/sddm-state.existed") || {
    echo "Missing SDDM state backup metadata." >&2
    return 1
  }

  case $existed in
    true)
      sudo test -f "$backup_dir/sddm-state.conf" || {
        echo "Missing SDDM state backup file." >&2
        return 1
      }
      parent=${state_file%/*}
      sudo install -d -m 0755 "$parent"
      temporary=$(sudo mktemp "$parent/.state.conf.frankenstein.XXXXXX")
      if ! sudo cp --preserve=all -- "$backup_dir/sddm-state.conf" "$temporary"; then
        sudo rm -f "$temporary"
        return 1
      fi
      sudo mv -f -- "$temporary" "$state_file"
      ;;
    false)
      sudo rm -f -- "$state_file"
      ;;
    *)
      echo "Invalid SDDM state backup metadata: $existed" >&2
      return 1
      ;;
  esac
}

frankenstein_choose_auto_default() {
  local active_desktop=$1 active_session=$2 autologin_session=$3
  local remembered_session=$4 omarchy_session=$5 plasma_session=$6

  case "$active_desktop:$active_session" in
    KDE:*|KDE:*:*|*:plasma|*:plasmawayland)
      [[ -n $plasma_session ]] && {
        echo plasma.desktop
        return
      }
      ;;
    *Hyprland*:*|*:omarchy)
      [[ -n $omarchy_session ]] && {
        echo omarchy.desktop
        return
      }
      ;;
  esac

  autologin_session=${autologin_session##*/}
  case $autologin_session in
    plasma.desktop)
      [[ -n $plasma_session ]] && {
        echo plasma.desktop
        return
      }
      ;;
    omarchy.desktop)
      [[ -n $omarchy_session ]] && {
        echo omarchy.desktop
        return
      }
      ;;
  esac

  remembered_session=${remembered_session##*/}
  remembered_session=${remembered_session% }
  case $remembered_session in
    plasma.desktop)
      [[ -n $plasma_session ]] && {
        echo plasma.desktop
        return
      }
      ;;
    omarchy.desktop)
      [[ -n $omarchy_session ]] && {
        echo omarchy.desktop
        return
      }
      ;;
  esac

  [[ -n $omarchy_session ]] && {
    echo omarchy.desktop
    return
  }
  [[ -n $plasma_session ]] && echo plasma.desktop
}
