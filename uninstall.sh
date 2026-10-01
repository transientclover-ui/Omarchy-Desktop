#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -Eeuo pipefail

readonly script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
if [[ -r $script_dir/installer-state ]]; then
  # shellcheck source=src/lib/installer-state.sh
  source "$script_dir/installer-state"
else
  # shellcheck source=src/lib/installer-state.sh
  source "$script_dir/src/lib/installer-state.sh"
fi

force=false
assume_yes=false

while (($#)); do
  case $1 in
    --force) force=true ;;
    --yes) assume_yes=true ;;
    --help|-h)
      echo "Usage: ./uninstall.sh [--yes] [--force]"
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

[[ $EUID -ne 0 ]] || {
  echo "Run this uninstaller as the user who installed Frankenstein." >&2
  exit 1
}

readonly state_dir=/var/lib/frankenstein
readonly sddm_state=/var/lib/sddm/state.conf
[[ -r $state_dir/current ]] || {
  echo "No active Frankenstein installation record was found." >&2
  exit 1
}

backup_id=$(cat "$state_dir/current")
state_file="$state_dir/installations/$backup_id.env"
[[ -r $state_file ]] || {
  echo "Installation state is missing: $state_file" >&2
  exit 1
}

# The state file is root-owned installer output containing only scalar values.
# shellcheck disable=SC1090
source "$state_file"
[[ $USER == "$INSTALL_USER" && $HOME == "$INSTALL_HOME" ]] || {
  echo "Run rollback as $INSTALL_USER with home $INSTALL_HOME." >&2
  exit 1
}

if [[ ${PACKAGE_MANAGED:-false} == true ]]; then
  template_dir=/usr/share/frankenstein/templates
  state_writer=/usr/lib/frankenstein/state
else
  project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
  template_dir=$project_dir/src
  state_writer=$project_dir/src/libexec/frankenstein-state
fi

if [[ $assume_yes != true ]]; then
  cat <<EOF
This will remove Frankenstein-owned integration and leave KDE packages and
configuration intact. A preserved existing Omarchy shell will not be changed.
Backups will remain at:
  $HOME/.local/state/frankenstein/backups/$backup_id
  $state_dir/backups/$backup_id
EOF
  printf 'Type UNINSTALL to continue: '
  read -r confirmation
  [[ $confirmation == UNINSTALL ]] || {
    echo "Uninstall cancelled."
    exit 0
  }
fi

# Older installation records used the filtered shell path.
case ${SHELL_MODE:-filtered} in
  preserve|filtered) ;;
  *) echo "Unknown shell mode; refusing uninstall." >&2; exit 1 ;;
esac
if [[ ${SHELL_MODE:-filtered} == filtered ]]; then
  if [[ $force != true ]]; then
    for path in \
      "$HOME/.config/systemd/user/frankenstein-omarchy-shell.service" \
      "$HOME/.config/autostart/frankenstein-omarchy-shell.desktop" \
      "$HOME/.local/share/applications/frankenstein-omarchy-menu.desktop"; do
      [[ -e $path ]] || continue
      case ${path##*/} in
        frankenstein-omarchy-shell.service)
          if [[ ${PACKAGE_MANAGED:-false} == true ]]; then
            source_path=$template_dir/frankenstein-omarchy-shell.service
          else
            source_path=$template_dir/systemd/frankenstein-omarchy-shell.service
          fi
          ;;
        frankenstein-omarchy-shell.desktop)
          if [[ ${PACKAGE_MANAGED:-false} == true ]]; then
            source_path=$template_dir/frankenstein-omarchy-shell.desktop
          else
            source_path=$template_dir/frankenstein/frankenstein-omarchy-shell-autostart.desktop
          fi
          ;;
        frankenstein-omarchy-menu.desktop)
          if [[ ${PACKAGE_MANAGED:-false} == true ]]; then
            source_path=$template_dir/frankenstein-omarchy-menu.desktop
          else
            source_path=$template_dir/frankenstein/frankenstein-omarchy-menu.desktop
          fi
          ;;
      esac
      cmp -s "$path" "$source_path" || {
        echo "Refusing to remove a modified file: $path" >&2
        echo "Review it or rerun with --force." >&2
        exit 1
      }
    done
  fi

  systemctl --user stop frankenstein-omarchy-shell.service 2>/dev/null || true
  rm -f \
    "$HOME/.config/autostart/frankenstein-omarchy-shell.desktop" \
    "$HOME/.config/systemd/user/frankenstein-omarchy-shell.service" \
    "$HOME/.local/share/applications/frankenstein-omarchy-menu.desktop"
  rm -f "$HOME/.config/frankenstein/shell-disabled"
  systemctl --user daemon-reload

  if [[ $EXISTING_SHELL_UNIT == true && $EXISTING_SHELL_ENABLED == true ]]; then
    systemctl --user enable omarchy-shell.service
  fi
  if [[ $EXISTING_SHELL_UNIT == true && $EXISTING_SHELL_ACTIVE == true ]]; then
    systemctl --user start omarchy-shell.service
  fi
fi

# Stop new activations, then wait for any in-flight writer before restoration.
if ! sudo systemctl disable --now omarchy-desktop-manager-default.path ||
   ! sudo systemctl stop omarchy-desktop-manager-default.service; then
  echo "Uninstall stopped: could not stop SDDM synchronization; installation record and backups retained." >&2
  exit 1
fi
if [[ ${SDDM_STATE_BACKED_UP:-false} == true ]]; then
  if ! frankenstein_restore_sddm_state \
    "$sddm_state" "$state_dir/backups/$backup_id"; then
    echo "Uninstall incomplete: could not restore SDDM state; installation record and backups retained at $state_dir/backups/$backup_id. Retry uninstall after resolving the restoration error." >&2
    exit 1
  fi
fi
if [[ $SDDM_OVERRIDE_CREATED == true ]]; then
  sudo rm -f /etc/sddm.conf.d/zzzz-frankenstein.conf
fi
"$state_writer" record-recovery \
  --backup-location "$state_dir/backups/$backup_id" >/dev/null
sudo rm -f \
  /etc/systemd/system/omarchy-desktop-manager-default.path \
  /etc/systemd/system/omarchy-desktop-manager-default.service
if [[ ${PACKAGE_MANAGED:-false} != true ]]; then
  sudo rm -f \
    /usr/lib/systemd/system/omarchy-desktop-manager-default.path \
    /usr/lib/systemd/system/omarchy-desktop-manager-default.service \
    /usr/bin/frankenstein-shell-adapter \
    /usr/bin/omarchy-default-desktop \
    /usr/bin/frankenstein-settings \
    /usr/bin/frankenstein-background \
    /usr/libexec/frankenstein-background-writer \
    /usr/lib/frankenstein/installer-state \
    /usr/lib/frankenstein/state \
    /usr/lib/frankenstein/diagnostics \
    /usr/lib/frankenstein/shell-profile \
    /usr/lib/frankenstein/set-default \
    /usr/share/frankenstein/profiles/plasma.json \
    /usr/share/frankenstein/profiles/plasma-menu.jsonc
  sudo rm -rf /usr/share/frankenstein/omarchy-shell
  sudo rm -rf /usr/share/sddm/themes/frankenstein
fi
sudo rm -rf /var/lib/omarchy-desktop-manager
sudo rm -f "$state_dir/current"
sudo systemctl daemon-reload

echo "Frankenstein integration removed."
echo "Backups were preserved. KDE packages installed during setup were not removed."
if [[ -s $HOME/.local/state/frankenstein/backups/$backup_id/packages-added.txt ]]; then
  echo "Packages added by the installer are listed in:"
  echo "  $HOME/.local/state/frankenstein/backups/$backup_id/packages-added.txt"
fi
echo "Log out and back in to complete session cleanup."
