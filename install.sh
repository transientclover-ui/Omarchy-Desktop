#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

set -Eeuo pipefail

readonly project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
readonly supported_omarchy_version=4.0.4-1
readonly system_state_dir=/var/lib/frankenstein
readonly installed_share=/usr/share/frankenstein
readonly sddm_state=/var/lib/sddm/state.conf

if [[ -r $project_dir/installer-state ]]; then
  # shellcheck source=src/lib/installer-state.sh
  source "$project_dir/installer-state"
else
  # shellcheck source=src/lib/installer-state.sh
  source "$project_dir/src/lib/installer-state.sh"
fi

assume_yes=false
preflight_only=false
requested_default=keep
requested_shell=auto
requested_login=preserve
mutation_started=false
payload_installed=false
sddm_override_created=false
default_path_enabled=false
user_files_installed=false
shell_unit_disabled=false
filtered_shell_started=false
sddm_state_backup_ready=false
user_state_written=false
user_state_existed=false
backup_id=
user_backup=
system_backup=
readonly user_sddm_state="${XDG_STATE_HOME:-$HOME/.local/state}/frankenstein/sddm-state.json"

rollback_partial_install() {
  local line=$1 status=$2
  trap - ERR INT TERM
  set +e

  if [[ $mutation_started != true ]]; then
    echo "Installation stopped before any changes were made (line $line)." >&2
    exit "$status"
  fi

  if [[ $filtered_shell_started == true ]]; then
    systemctl --user stop frankenstein-omarchy-shell.service
  fi
  if [[ $user_files_installed == true ]]; then
    rm -f \
      "$HOME/.config/autostart/frankenstein-omarchy-shell.desktop" \
      "$HOME/.config/systemd/user/frankenstein-omarchy-shell.service" \
      "$HOME/.local/share/applications/frankenstein-omarchy-menu.desktop"
    systemctl --user daemon-reload
  fi
  if [[ $user_state_written == true ]]; then
    if [[ $user_state_existed == true ]]; then
      install -Dm0600 "$user_backup/sddm-state.before.json" "$user_sddm_state"
    else
      rm -f "$user_sddm_state"
    fi
  fi
  if [[ $shell_unit_disabled == true ]]; then
    [[ $existing_shell_enabled == true ]] &&
      systemctl --user enable omarchy-shell.service
    [[ $existing_shell_active == true ]] &&
      systemctl --user start omarchy-shell.service
  fi
  if [[ $default_path_enabled == true ]]; then
    # A path unit can already have launched its independent oneshot service.
    # Stop the trigger first, then wait for the writer before restoring state.
    if ! sudo systemctl disable --now omarchy-desktop-manager-default.path ||
       ! sudo systemctl stop omarchy-desktop-manager-default.service; then
      echo "Rollback incomplete: could not stop SDDM synchronization; backups retained at $system_backup." >&2
      exit "$status"
    fi
  fi
  if [[ $sddm_state_backup_ready == true ]]; then
    if ! frankenstein_restore_sddm_state "$sddm_state" "$system_backup"; then
      echo "Rollback incomplete: could not restore SDDM state; recovery data retained at $system_backup." >&2
      exit "$status"
    fi
  fi
  if [[ $sddm_override_created == true ]]; then
    sudo rm -f /etc/sddm.conf.d/zzzz-frankenstein.conf
  fi
  sudo rm -rf /var/lib/omarchy-desktop-manager

  if [[ $payload_installed == true ]]; then
    sudo rm -f \
      /usr/bin/frankenstein-shell-adapter \
      /usr/bin/omarchy-default-desktop \
      /usr/bin/frankenstein-settings \
      /usr/bin/frankenstein-background \
      /usr/lib/frankenstein/set-default \
      /usr/libexec/frankenstein-background-writer \
      /usr/lib/frankenstein/installer-state \
      /usr/lib/frankenstein/state \
      /usr/lib/frankenstein/diagnostics \
      /usr/lib/frankenstein/sddm-validate \
      /usr/lib/frankenstein/shell-profile \
      /usr/lib/systemd/system/omarchy-desktop-manager-default.path \
      /usr/lib/systemd/system/omarchy-desktop-manager-default.service
    sudo rm -rf /usr/share/frankenstein/omarchy-shell
    sudo rm -rf /usr/share/sddm/themes/frankenstein
    sudo rm -f \
      /usr/share/frankenstein/profiles/plasma.json \
      /usr/share/frankenstein/profiles/plasma-menu.jsonc
  fi

  [[ -z $backup_id ]] || sudo rm -f "$system_state_dir/installations/$backup_id.env"
  sudo rm -f "$system_state_dir/current"
  sudo systemctl daemon-reload

  echo "Installation failed at line $line; completed mutations were rolled back." >&2
  if [[ -n $user_backup && -s $user_backup/packages-added.txt ]]; then
    echo "Packages were not removed. Review: $user_backup/packages-added.txt" >&2
  fi
  exit "$status"
}

handle_signal() {
  rollback_partial_install "$1" 130
}

trap 'rollback_partial_install "$LINENO" "$?"' ERR
trap 'handle_signal "$LINENO"' INT TERM

usage() {
  cat <<'EOF'
Usage: ./install.sh [--preflight] [--yes] [--shell auto|preserve|filtered]
                    [--login preserve|chooser|frankenstein]
                    [--default keep|auto|omarchy|plasma]

  --preflight       Run read-only checks and print the proposed changes.
  --yes             Confirm the printed plan non-interactively.
  --shell VALUE     auto preserves an existing shell; otherwise adds a filtered menu.
                    preserve requires an existing shell; filtered explicitly replaces it.
  --login VALUE     preserve (default) leaves theme/autologin unchanged; chooser
                    requests a reversible Breeze/no-autologin override; frankenstein
                    requests the packaged session-first theme with the same safeguards.
  --default VALUE   keep (default) leaves remembered session state unchanged;
                    auto selects the active supported desktop; or choose a desktop.
EOF
}

while (($#)); do
  case $1 in
    --preflight) preflight_only=true ;;
    --yes) assume_yes=true ;;
    --shell)
      shift
      requested_shell=${1:-}
      [[ $requested_shell =~ ^(auto|preserve|filtered)$ ]] || {
        echo "Invalid shell integration: $requested_shell" >&2; exit 2
      }
      ;;
    --login)
      shift
      requested_login=${1:-}
      [[ $requested_login =~ ^(preserve|chooser|frankenstein)$ ]] || {
        echo "Invalid login integration: $requested_login" >&2; exit 2
      }
      ;;
    --default)
      shift
      requested_default=${1:-}
      [[ $requested_default =~ ^(keep|auto|omarchy|plasma)$ ]] || {
        echo "Invalid default desktop: $requested_default" >&2
        exit 2
      }
      ;;
    --help|-h) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

[[ $EUID -ne 0 ]] || {
  echo "Run this installer as the target desktop user, not as root." >&2
  exit 1
}

required_commands=(awk cp find grep install jq pacman sed sha256sum sudo systemctl tar)
missing_commands=()
for command_name in "${required_commands[@]}"; do
  command -v "$command_name" >/dev/null 2>&1 || missing_commands+=("$command_name")
done
((${#missing_commands[@]} == 0)) || {
  printf 'Missing required commands: %s\n' "${missing_commands[*]}" >&2
  exit 1
}

[[ -r /etc/os-release ]] || {
  echo "Cannot identify the operating system." >&2
  exit 1
}
. /etc/os-release
case " ${ID:-} ${ID_LIKE:-} " in
  *" omarchy "*|*" arch "*) ;;
  *)
  echo "Unsupported operating system: ${ID:-unknown}; Omarchy or Arch Linux is required." >&2
  exit 1
  ;;
esac

omarchy_version=$(pacman -Q omarchy 2>/dev/null | awk '{print $2}')
[[ $omarchy_version == "$supported_omarchy_version" ]] || {
  echo "Unsupported Omarchy version: ${omarchy_version:-not installed}" >&2
  echo "This installer is verified only with Omarchy $supported_omarchy_version." >&2
  exit 1
}

package_managed=false
if pacman -Q frankenstein-core >/dev/null 2>&1 &&
   pacman -Q frankenstein-kde >/dev/null 2>&1; then
  package_managed=true
fi

if [[ $package_managed == true ]]; then
  shell_service_source=$installed_share/templates/frankenstein-omarchy-shell.service
  shell_autostart_source=$installed_share/templates/frankenstein-omarchy-shell.desktop
  menu_desktop_source=$installed_share/templates/frankenstein-omarchy-menu.desktop
  sddm_override_source=$installed_share/templates/zzzz-omarchy-desktop-manager.conf
  state_writer=/usr/lib/frankenstein/state
  sddm_validator=/usr/lib/frankenstein/sddm-validate
  payload_files=(
    /usr/bin/frankenstein-shell-adapter
    /usr/bin/omarchy-default-desktop
    /usr/bin/frankenstein-settings
    /usr/bin/frankenstein-background
    /usr/libexec/frankenstein-background-writer
    /usr/lib/frankenstein/set-default
    /usr/lib/frankenstein/state
    /usr/lib/frankenstein/diagnostics
    /usr/lib/frankenstein/sddm-validate
    "$installed_share/omarchy-shell/shell.qml"
    "$installed_share/omarchy-shell/services/PluginRegistry.qml"
    "$installed_share/omarchy-shell/plugins/menu/Menu.qml"
    "$installed_share/profiles/plasma.json"
    "$installed_share/profiles/plasma-menu.jsonc"
    /usr/share/sddm/themes/frankenstein/Main.qml
    /usr/share/sddm/themes/frankenstein/metadata.desktop
    /usr/share/sddm/themes/frankenstein/theme.conf
    /usr/share/sddm/themes/frankenstein/backgrounds/vaporwave-default.png
    /usr/lib/frankenstein/installer-state
    /usr/lib/frankenstein/shell-profile
    /usr/lib/systemd/system/omarchy-desktop-manager-default.path
    /usr/lib/systemd/system/omarchy-desktop-manager-default.service
    "$shell_service_source"
    "$shell_autostart_source"
    "$menu_desktop_source"
    "$sddm_override_source"
  )
else
  shell_service_source=$project_dir/src/systemd/frankenstein-omarchy-shell.service
  shell_autostart_source=$project_dir/src/frankenstein/frankenstein-omarchy-shell-autostart.desktop
  menu_desktop_source=$project_dir/src/frankenstein/frankenstein-omarchy-menu.desktop
  sddm_override_source=$project_dir/src/frankenstein/zzzz-frankenstein.conf
  state_writer=$project_dir/src/libexec/frankenstein-state
  sddm_validator=$project_dir/src/libexec/frankenstein-sddm-validate
  payload_files=(
    "$project_dir/src/bin/frankenstein-shell-adapter"
    "$project_dir/src/bin/omarchy-default-desktop"
    "$project_dir/src/bin/frankenstein-settings"
    "$project_dir/src/bin/frankenstein-background"
    "$project_dir/src/libexec/frankenstein-background-writer"
    "$project_dir/src/libexec/omarchy-desktop-manager-set-default"
    "$project_dir/src/frankenstein/omarchy-shell/shell.qml"
    "$project_dir/src/frankenstein/omarchy-shell/services/PluginRegistry.qml"
    "$project_dir/src/frankenstein/omarchy-shell/plugins/menu/Menu.qml"
    "$project_dir/src/frankenstein/plasma-shell-profile.json"
    "$project_dir/src/frankenstein/plasma-menu.jsonc"
    "$project_dir/src/sddm/frankenstein/Main.qml"
    "$project_dir/src/sddm/frankenstein/metadata.desktop"
    "$project_dir/src/sddm/frankenstein/theme.conf"
    "$project_dir/src/sddm/frankenstein/backgrounds/vaporwave-default.png"
    "$project_dir/src/lib/installer-state.sh"
    "$project_dir/src/libexec/frankenstein-state"
    "$project_dir/src/libexec/frankenstein-diagnostics"
    "$project_dir/src/libexec/frankenstein-sddm-validate"
    "$project_dir/src/lib/shell-profile.sh"
    "$shell_service_source"
    "$shell_autostart_source"
    "$menu_desktop_source"
    "$sddm_override_source"
  )
fi

for source_file in "${payload_files[@]}"; do
  [[ -r $source_file ]] || {
    echo "Installer payload is incomplete: $source_file" >&2
    exit 1
  }
done

[[ -r /usr/share/omarchy/shell/shell.qml &&
   -r /usr/share/omarchy/shell/services/PluginRegistry.qml &&
   -r /usr/share/omarchy/shell/plugins/menu/Menu.qml ]] || {
  echo "The installed Omarchy Shell source layout is unsupported." >&2
  exit 1
}

grep -q 'property PluginRegistry pluginRegistry' /usr/share/omarchy/shell/shell.qml
grep -q 'function isEnabled(id)' /usr/share/omarchy/shell/services/PluginRegistry.qml
grep -q 'function rebuildItemsFromSources()' /usr/share/omarchy/shell/plugins/menu/Menu.qml

desktop_value() {
  local key=$1 file=$2
  awk -F= -v wanted="$key" '
    /^\[Desktop Entry\]$/ { in_entry=1; next }
    /^\[/ { in_entry=0 }
    in_entry && $1 == wanted {
      sub(/^[^=]*=/, "")
      print
      exit
    }
  ' "$file"
}

valid_session_file() {
  local file=$1 type try_exec
  [[ -f $file && -r $file ]] || return 1
  type=$(desktop_value Type "$file")
  [[ -z $type || $type == Application ]] || return 1
  [[ -n $(desktop_value Name "$file") && -n $(desktop_value Exec "$file") ]] || return 1
  try_exec=$(desktop_value TryExec "$file")
  if [[ -n $try_exec ]]; then
    if [[ $try_exec == /* ]]; then
      [[ -x $try_exec ]] || return 1
    else
      command -v "$try_exec" >/dev/null 2>&1 || return 1
    fi
  fi
}

find_session() {
  local id=$1 dir file
  for dir in /usr/local/share/wayland-sessions /usr/share/wayland-sessions \
             /usr/local/share/xsessions /usr/share/xsessions; do
    file="$dir/$id"
    if valid_session_file "$file"; then
      printf '%s\n' "$file"
      return 0
    fi
  done
  return 1
}

omarchy_session=$(find_session omarchy.desktop) || {
  echo "The preserved Omarchy session is missing or invalid; refusing installation." >&2
  exit 1
}

plasma_session=$(find_session plasma.desktop 2>/dev/null || true)
plasma_action=adopt
if [[ -z $plasma_session ]]; then
  plasma_action=install
fi

effective_sddm_value() {
  local wanted_section=$1 wanted_key=$2 proposed=${3:-false} file result value dir
  local -a files=()
  # SDDM reads vendor fragments, local fragments, then the legacy main file.
  for dir in /usr/lib/sddm/sddm.conf.d /etc/sddm.conf.d; do
    while IFS= read -r file; do files+=("$file"); done < <(
      {
        [[ ! -d $dir ]] || find "$dir" -maxdepth 1 \( -type f -o -type l \) -name '*.conf' -print
        if [[ $proposed == true && $dir == /etc/sddm.conf.d ]]; then
          printf '%s\n' /etc/sddm.conf.d/zzzz-frankenstein.conf
        fi
      } | LC_ALL=C sort -u
    )
  done
  [[ ! -f /etc/sddm.conf ]] || files+=(/etc/sddm.conf)
  result=
  for file in "${files[@]}"; do
    if [[ $proposed == true && $file == /etc/sddm.conf.d/zzzz-frankenstein.conf ]]; then
      file=$sddm_override_source
      if [[ $wanted_section == Theme && $wanted_key == Current &&
            -n ${proposed_theme:-} ]]; then
        result=$proposed_theme
        continue
      fi
    fi
    value=$(awk -F= -v section="$wanted_section" -v key="$wanted_key" '
      /^[[:space:]]*[#;]/ { next }
      { sub(/\r$/, ""); sub(/^[[:space:]]+/, ""); sub(/[[:space:]]+$/, "") }
      $0 == "[" section "]" { active=1; next }
      /^\[/ { active=0 }
      active {
        name=$1
        sub(/[[:space:]]+$/, "", name)
        if (name == key) {
          sub(/^[^=]*=[[:space:]]*/, "")
          value=$0
          found=1
        }
      }
      END { if (found) printf "set:%s", value }
    ' "$file")
    [[ $value == set:* ]] && result=${value#set:}
  done
  printf '%s\n' "$result"
}


existing_shell_unit=false
existing_shell_enabled=false
existing_shell_active=false
if [[ -e $HOME/.config/systemd/user/omarchy-shell.service || -L $HOME/.config/systemd/user/omarchy-shell.service ]] ||
   [[ $(systemctl --user show omarchy-shell.service -p LoadState --value 2>/dev/null || true) == loaded ]]; then
  existing_shell_unit=true
  systemctl --user is-enabled omarchy-shell.service >/dev/null 2>&1 && existing_shell_enabled=true
  systemctl --user is-active omarchy-shell.service >/dev/null 2>&1 && existing_shell_active=true
fi

# An existing shell belongs to the user. Do not substitute a reduced profile
# or change its enablement just to add desktop-selection integration.
shell_mode=filtered
if [[ $requested_shell == preserve && $existing_shell_unit != true ]]; then
  echo "No existing Omarchy shell service to preserve; refusing to guess a replacement." >&2
  exit 1
fi
if [[ $requested_shell != filtered && $existing_shell_unit == true ]]; then
  shell_mode=preserve
fi

[[ ! -e $system_state_dir/current && ! -L $system_state_dir/current ]] || {
  echo "Frankenstein already has an active installation record." >&2
  echo "Run ./uninstall.sh before reinstalling." >&2
  exit 1
}

system_conflicting_paths=(
  /usr/bin/frankenstein-shell-adapter
  /usr/bin/omarchy-default-desktop
  /usr/bin/frankenstein-settings
  /usr/bin/frankenstein-background
  /usr/lib/frankenstein/set-default
  /usr/libexec/frankenstein-background-writer
  /usr/lib/frankenstein/installer-state
  /usr/lib/frankenstein/state
  /usr/lib/frankenstein/diagnostics
  /usr/lib/frankenstein/sddm-validate
  /usr/lib/frankenstein/shell-profile
  /usr/share/frankenstein/omarchy-shell
  /usr/share/frankenstein/profiles/plasma.json
  /usr/share/frankenstein/profiles/plasma-menu.jsonc
  /usr/share/sddm/themes/frankenstein
  /usr/lib/systemd/system/omarchy-desktop-manager-default.path
  /usr/lib/systemd/system/omarchy-desktop-manager-default.service
)
configuration_conflicting_paths=(
  /var/lib/omarchy-desktop-manager
  /etc/sddm.conf.d/zzzz-frankenstein.conf
  "$HOME/.config/systemd/user/frankenstein-omarchy-shell.service"
  "$HOME/.config/autostart/frankenstein-omarchy-shell.desktop"
  "$HOME/.local/share/applications/frankenstein-omarchy-menu.desktop"
)
if [[ $package_managed != true ]]; then
  for conflicting_path in "${system_conflicting_paths[@]}"; do
    [[ ! -e $conflicting_path && ! -L $conflicting_path ]] || {
      echo "Unmanaged Frankenstein path already exists: $conflicting_path" >&2
      echo "Move or remove it before installation so it cannot be overwritten." >&2
      exit 1
    }
  done
fi
for conflicting_path in "${configuration_conflicting_paths[@]}"; do
  [[ ! -e $conflicting_path && ! -L $conflicting_path ]] || {
    echo "Integration path already exists: $conflicting_path" >&2
    echo "Move or remove it before installation so it cannot be overwritten." >&2
    exit 1
  }
done

sddm_theme=$(effective_sddm_value Theme Current)
autologin_user=$(effective_sddm_value Autologin User)
autologin_session=$(effective_sddm_value Autologin Session)
sddm_action=preserve
if [[ $requested_login == chooser && ( $sddm_theme != breeze || -n $autologin_user || -n $autologin_session ) ]]; then
  sddm_action=add-reversible-breeze-override
elif [[ $requested_login == frankenstein && ( $sddm_theme != frankenstein || -n $autologin_user || -n $autologin_session ) ]]; then
  sddm_action=add-reversible-frankenstein-override
fi

# Theme validation is independent from Plasma appearance and must complete
# before backups, package installation, or SDDM configuration changes begin.
if [[ $requested_login == frankenstein ]]; then
  if [[ $package_managed == true ]]; then
    "$sddm_validator" /usr/share/sddm/themes/frankenstein
  else
    "$sddm_validator" "$project_dir/src/sddm/frankenstein"
  fi
fi

# Refuse configurations whose higher-precedence settings defeat our fragment.
# Do not rewrite an existing administrator-owned file to force the plan through.
if [[ $sddm_action == add-reversible-breeze-override ||
      $sddm_action == add-reversible-frankenstein-override ]]; then
  proposed_theme=breeze
  [[ $sddm_action != add-reversible-frankenstein-override ]] || proposed_theme=frankenstein
  for setting in "Theme Current $proposed_theme" 'Autologin User' 'Autologin Session' \
                 'Autologin Relogin false' 'Users RememberLastUser true' \
                 'Users RememberLastSession true'; do
    read -r section key expected <<<"$setting"
    actual=$(effective_sddm_value "$section" "$key" true)
    [[ $actual == "$expected" ]] || {
      echo "SDDM configuration overrides the proposed $section/$key setting; refusing installation. Review higher-precedence configuration first." >&2
      exit 1
    }
  done
fi

if [[ $requested_default == keep ]]; then
  default_session=unchanged
elif [[ $requested_default == auto ]]; then
  active_desktop=${XDG_CURRENT_DESKTOP:-}
  active_session=${DESKTOP_SESSION:-}
  if [[ -z $active_desktop || -z $active_session ]]; then
    user_environment=$(systemctl --user show-environment 2>/dev/null || true)
    [[ -n $active_desktop ]] ||
      active_desktop=$(sed -n 's/^XDG_CURRENT_DESKTOP=//p' <<<"$user_environment" | tail -n 1)
    [[ -n $active_session ]] ||
      active_session=$(sed -n 's/^DESKTOP_SESSION=//p' <<<"$user_environment" | tail -n 1)
  fi
  remembered_session=
  if [[ -r $sddm_state ]]; then
    remembered_session=$(awk -F= '$1 == "Session" { print $2; exit }' "$sddm_state")
  fi
  default_session=$(frankenstein_choose_auto_default \
    "$active_desktop" "$active_session" "$autologin_session" \
    "$remembered_session" "$omarchy_session" "$plasma_session")
  [[ -n $default_session ]] || {
    echo "No supported default desktop session is available." >&2
    exit 1
  }
else
  default_session=$requested_default.desktop
fi

cat <<EOF
Frankenstein KDE compatibility preflight

  Omarchy version:       $omarchy_version
  Omarchy session:       $omarchy_session
  Plasma session:        ${plasma_session:-not installed}
  Plasma action:         $plasma_action
  SDDM theme:            ${sddm_theme:-not configured}
  SDDM action:           $sddm_action
  Initial default:       $default_session
  Shell integration:     $shell_mode
  Existing shell unit:   $existing_shell_unit
  Shell unit enabled:    $existing_shell_enabled
  Shell unit active:     $existing_shell_active

Planned preservation:
  - Do not edit KDE panels, wallpaper, themes, shortcuts, KWin, lock, or input settings.
  - Back up the complete ~/.config/omarchy tree and relevant KDE configuration.
  - Back up SDDM configuration and both desktop-session entries.
  - Preserve the original Omarchy session and packaged Omarchy Shell.
  - Keep the existing Omarchy menu extension unchanged; load a separate Plasma profile.

Planned changes:
  - ${plasma_action^} KDE Plasma packages.
  - Install the KDE integration payload and compatibility checks.
  - Add validated default-desktop helpers and state synchronization.
  - SDDM: $sddm_action.
  - Payload ownership: $([[ $package_managed == true ]] && echo pacman || echo standalone installer).

No service or display-manager restart will be performed. Log out normally after
installation and choose Plasma from SDDM to complete verification.
EOF

if [[ $shell_mode == preserve ]]; then
  echo "Existing Omarchy shell: preserve its service, configuration, bar, plugins and disabled choices."
  echo "No filtered shell, replacement autostart or shell service changes will be made."
  echo "This preserves the existing setup; it does not certify every enabled plugin."
else
  echo "Add the menu-only KDE adapter and autostart; existing configuration files remain intact."
  if [[ $existing_shell_unit == true ]]; then
    echo "Explicit filtered choice: stop/disable the existing shell service; its bar and other plugins will not run in the filtered shell."
  fi
fi

if [[ $requested_login == preserve ]]; then
  echo "Keep the current SDDM theme and autologin settings."
  if [[ -n $autologin_user || -n $autologin_session ]]; then
    echo "Existing autologin may override chooser/default selection; it will not be disabled automatically."
  fi
fi
if [[ $requested_default == keep ]]; then
  echo "Keep remembered desktop state; no Frankenstein default is imposed until you choose one."
fi

if [[ $preflight_only == true ]]; then
  exit 0
fi

if [[ $assume_yes != true ]]; then
  printf '\nType INSTALL to approve these changes: '
  read -r confirmation
  [[ $confirmation == INSTALL ]] || {
    echo "Installation cancelled."
    exit 0
  }
fi

sudo -v

backup_id=$(date -u +%Y%m%dT%H%M%SZ)
user_backup="$HOME/.local/state/frankenstein/backups/$backup_id"
system_backup="$system_state_dir/backups/$backup_id"
mkdir -p "$user_backup"
sudo install -d -m 0700 "$system_backup"
mutation_started=true
if [[ -e $user_sddm_state || -L $user_sddm_state ]]; then
  [[ -f $user_sddm_state && ! -L $user_sddm_state ]] || {
    echo "Refusing non-regular existing state file: $user_sddm_state" >&2
    exit 1
  }
  user_state_existed=true
  install -m 0600 "$user_sddm_state" "$user_backup/sddm-state.before.json"
fi

frankenstein_backup_sddm_state "$sddm_state" "$system_backup"
sddm_state_backup_ready=true

user_paths=()
for relative in \
  .config/omarchy \
  .config/hypr \
  .config/plasma-org.kde.plasma.desktop-appletsrc \
  .config/kdeglobals \
  .config/kwinrc \
  .config/kglobalshortcutsrc \
  .config/plasmarc \
  .config/kcminputrc \
  .config/kscreenlockerrc \
  .config/kwinoutputconfig.json \
  .config/ksmserverrc \
  .config/powermanagementprofilesrc \
  .config/Trolltech.conf \
  .config/systemd/user/omarchy-shell.service \
  .config/autostart \
  .local/share/plasma \
  .local/share/color-schemes \
  .local/share/icons; do
  [[ -e $HOME/$relative ]] && user_paths+=("$relative")
done
printf '%s\n' "${user_paths[@]}" >"$user_backup/paths"
if ((${#user_paths[@]})); then
  tar -C "$HOME" -cpf "$user_backup/user-config.tar" "${user_paths[@]}"
  find "${user_paths[@]/#/$HOME/}" -type f -exec sha256sum {} + \
    >"$user_backup/sha256-before.txt"
fi

system_paths=()
for absolute in \
  /etc/sddm.conf \
  /etc/sddm.conf.d \
  "$omarchy_session" \
  /usr/share/wayland-sessions/plasma.desktop; do
  [[ -e $absolute ]] && system_paths+=("${absolute#/}")
done
printf '%s\n' "${system_paths[@]}" | sudo tee "$system_backup/paths" >/dev/null
if ((${#system_paths[@]})); then
  sudo tar -C / -cpf "$system_backup/system-config.tar" "${system_paths[@]}"
  for path in "${system_paths[@]}"; do
    sudo find "/$path" -type f -exec sha256sum {} +
  done | sudo tee "$system_backup/sha256-before.txt" >/dev/null
fi

pacman -Qq | sort >"$user_backup/packages-before.txt"

if [[ $plasma_action == install ]]; then
  omarchy pkg add plasma-meta
  plasma_session=$(find_session plasma.desktop) || {
    echo "Plasma installation completed without a valid plasma.desktop session." >&2
    exit 1
  }
fi

for command_name in quickshell qs systemsettings xdg-terminal-exec qdbus6; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "Required Plasma integration command is missing after package installation: $command_name" >&2
    exit 1
  }
done

pacman -Qq | sort >"$user_backup/packages-after.txt"
comm -13 "$user_backup/packages-before.txt" "$user_backup/packages-after.txt" \
  >"$user_backup/packages-added.txt"

sudo install -d -m 0755 "$system_state_dir/installations"

if [[ $package_managed != true ]]; then
  payload_installed=true
  sudo install -d -m 0755 \
    /usr/lib/frankenstein \
    "$installed_share/omarchy-shell/services" \
    "$installed_share/omarchy-shell/plugins/menu" \
    "$installed_share/profiles" \
    /usr/share/sddm/themes/frankenstein/backgrounds \
    /usr/lib/systemd/system

  sudo install -m 0755 "$project_dir/src/bin/frankenstein-shell-adapter" \
    /usr/bin/frankenstein-shell-adapter
  sudo install -m 0755 "$project_dir/src/bin/frankenstein-settings" \
    /usr/bin/frankenstein-settings
  sudo install -m 0755 "$project_dir/src/bin/frankenstein-background" \
    /usr/bin/frankenstein-background
  sudo install -m 0755 "$project_dir/src/libexec/frankenstein-background-writer" \
    /usr/libexec/frankenstein-background-writer
  sudo install -m 0755 "$project_dir/src/bin/omarchy-default-desktop" \
    /usr/bin/omarchy-default-desktop
  sudo install -m 0755 "$project_dir/src/libexec/omarchy-desktop-manager-set-default" \
    /usr/lib/frankenstein/set-default
  sudo install -m 0644 "$project_dir/src/lib/installer-state.sh" \
    /usr/lib/frankenstein/installer-state
  sudo install -m 0755 "$project_dir/src/libexec/frankenstein-state" \
    /usr/lib/frankenstein/state
  sudo install -m 0755 "$project_dir/src/libexec/frankenstein-diagnostics" \
    /usr/lib/frankenstein/diagnostics
  sudo install -m 0755 "$project_dir/src/libexec/frankenstein-sddm-validate" \
    /usr/lib/frankenstein/sddm-validate
  sudo install -m 0644 "$project_dir/src/lib/shell-profile.sh" \
    /usr/lib/frankenstein/shell-profile
  sudo install -m 0644 "$project_dir/src/frankenstein/plasma-shell-profile.json" \
    "$installed_share/profiles/plasma.json"
  sudo install -m 0644 "$project_dir/src/frankenstein/plasma-menu.jsonc" \
    "$installed_share/profiles/plasma-menu.jsonc"
  sudo install -m 0644 "$project_dir/src/sddm/frankenstein/Main.qml" \
    /usr/share/sddm/themes/frankenstein/Main.qml
  sudo install -m 0644 "$project_dir/src/sddm/frankenstein/metadata.desktop" \
    /usr/share/sddm/themes/frankenstein/metadata.desktop
  sudo install -m 0644 "$project_dir/src/sddm/frankenstein/theme.conf" \
    /usr/share/sddm/themes/frankenstein/theme.conf
  sudo install -m 0644 \
    "$project_dir/src/sddm/frankenstein/backgrounds/vaporwave-default.png" \
    /usr/share/sddm/themes/frankenstein/backgrounds/vaporwave-default.png
  sudo install -m 0644 "$project_dir/src/frankenstein/omarchy-shell/shell.qml" \
    "$installed_share/omarchy-shell/shell.qml"
  sudo install -m 0644 \
    "$project_dir/src/frankenstein/omarchy-shell/services/PluginRegistry.qml" \
    "$installed_share/omarchy-shell/services/PluginRegistry.qml"
  sudo install -m 0644 \
    "$project_dir/src/frankenstein/omarchy-shell/plugins/menu/Menu.qml" \
    "$installed_share/omarchy-shell/plugins/menu/Menu.qml"
  sudo install -m 0644 "$project_dir/src/systemd/omarchy-desktop-manager-default.path" \
    /usr/lib/systemd/system/omarchy-desktop-manager-default.path
  sudo install -m 0644 "$project_dir/src/systemd/omarchy-desktop-manager-default.service" \
    /usr/lib/systemd/system/omarchy-desktop-manager-default.service
fi

if [[ $package_managed != true ]]; then
  sudo ln -sfn /usr/share/omarchy/shell/Commons "$installed_share/omarchy-shell/Commons"
  sudo ln -sfn /usr/share/omarchy/shell/Ui "$installed_share/omarchy-shell/Ui"
  # QML resolves Bar even when the KDE profile disables its instance.
  sudo ln -sfn /usr/share/omarchy/shell/plugins/bar "$installed_share/omarchy-shell/plugins/bar"
  for source in /usr/share/omarchy/shell/services/*; do
    name=${source##*/}
    [[ $name == PluginRegistry.qml ]] && continue
    sudo ln -sfn "$source" "$installed_share/omarchy-shell/services/$name"
  done
  for source in /usr/share/omarchy/shell/plugins/menu/*; do
    name=${source##*/}
    [[ $name == Menu.qml ]] && continue
    sudo ln -sfn "$source" "$installed_share/omarchy-shell/plugins/menu/$name"
  done
fi

if [[ $sddm_action == add-reversible-breeze-override ||
      $sddm_action == add-reversible-frankenstein-override ]]; then
  sddm_override_created=true
  sudo install -m 0644 "$sddm_override_source" \
    /etc/sddm.conf.d/zzzz-frankenstein.conf
  configured_theme=breeze
  [[ $sddm_action != add-reversible-frankenstein-override ]] || configured_theme=frankenstein
  sudo sed -i "s/^Current=.*/Current=$configured_theme/" /etc/sddm.conf.d/zzzz-frankenstein.conf
fi

sudo systemctl daemon-reload
default_path_enabled=true
sudo systemctl enable --now omarchy-desktop-manager-default.path
if [[ $default_session != unchanged ]]; then
  sudo /usr/lib/frankenstein/set-default "$default_session"
fi

if [[ $shell_mode == filtered ]]; then
  install -d -m 0755 \
    "$HOME/.config/systemd/user" \
    "$HOME/.config/autostart" \
    "$HOME/.local/share/applications"
  user_files_installed=true
  install -m 0644 "$shell_service_source" \
    "$HOME/.config/systemd/user/frankenstein-omarchy-shell.service"
  install -m 0644 "$shell_autostart_source" \
    "$HOME/.config/autostart/frankenstein-omarchy-shell.desktop"
  install -m 0644 "$menu_desktop_source" \
    "$HOME/.local/share/applications/frankenstein-omarchy-menu.desktop"

  if [[ $existing_shell_unit == true ]]; then
    shell_unit_disabled=true
    systemctl --user disable --now omarchy-shell.service
  fi
  systemctl --user daemon-reload

  current_desktop=${XDG_CURRENT_DESKTOP:-}
  if [[ $current_desktop == KDE* ]]; then
    filtered_shell_started=true
    systemctl --user start frankenstein-omarchy-shell.service
  fi
fi

cat >"$user_backup/install-state.env" <<EOF
BACKUP_ID=$backup_id
INSTALL_USER=$USER
INSTALL_HOME=$HOME
EXISTING_SHELL_UNIT=$existing_shell_unit
EXISTING_SHELL_ENABLED=$existing_shell_enabled
EXISTING_SHELL_ACTIVE=$existing_shell_active
SDDM_OVERRIDE_CREATED=$sddm_override_created
DEFAULT_SESSION=$default_session
PLASMA_ACTION=$plasma_action
PACKAGE_MANAGED=$package_managed
SDDM_STATE_BACKED_UP=true
SHELL_MODE=$shell_mode
PREVIOUS_SDDM_THEME=$sddm_theme
REQUESTED_LOGIN=$requested_login
EOF
sudo install -m 0644 "$user_backup/install-state.env" \
  "$system_state_dir/installations/$backup_id.env"
printf '%s\n' "$backup_id" | sudo tee "$system_state_dir/current" >/dev/null

state_arguments=(
  record-install
  --previous-theme "$sddm_theme"
  --backup-location "$system_backup"
  --configuration-path /etc/sddm.conf.d/zzzz-frankenstein.conf
  --session "${omarchy_session##*/}"
)
[[ -z $plasma_session ]] || state_arguments+=(--session "${plasma_session##*/}")
[[ $requested_login != frankenstein ]] || state_arguments+=(--theme-active)
"$state_writer" "${state_arguments[@]}" >/dev/null
user_state_written=true
trap - ERR INT TERM

echo
echo "Frankenstein installation completed."
echo "User backup:   $user_backup"
echo "System backup: $system_backup"
echo "Log out normally, choose Plasma in SDDM, then run:"
echo "  frankenstein-shell-adapter check"
if [[ $shell_mode == preserve ]]; then
  echo "Your existing Omarchy shell was preserved; the check does not certify plugin compatibility."
fi
echo
echo "Rollback:"
if [[ $package_managed == true ]]; then
  echo "  frankenstein uninstall"
else
  echo "  $project_dir/uninstall.sh"
fi
