#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

frankenstein_validate_base_shell_profile() {
  local profile=$1

  jq -e '
    type == "object" and
    .schemaVersion == 1 and
    (.id | type == "string" and length > 0) and
    (.desktop | type == "string" and length > 0) and
    (.shell | type == "object") and
    (.shell.enabledPlugins | type == "array") and
    (all(.shell.enabledPlugins[];
      type == "string" and test("^[A-Za-z0-9._-]+$"))) and
    ((.shell.enabledPlugins | length) == (.shell.enabledPlugins | unique | length)) and
    (.shell.panel == "native" or .shell.panel == "omarchy")
  ' "$profile" >/dev/null
}

frankenstein_validate_shell_profile_override() {
  local profile=$1

  jq -e '
    type == "object" and
    .schemaVersion == 1 and
    ((keys - ["schemaVersion", "shell"]) | length == 0) and
    (.shell | type == "object") and
    ((.shell | keys - ["enabledPlugins", "panel"]) | length == 0) and
    (.shell | has("enabledPlugins") or has("panel")) and
    ((.shell | has("enabledPlugins") | not) or
      ((.shell.enabledPlugins | type == "array") and
       all(.shell.enabledPlugins[];
         type == "string" and test("^[A-Za-z0-9._-]+$")) and
       ((.shell.enabledPlugins | length) ==
        (.shell.enabledPlugins | unique | length)))) and
    ((.shell | has("panel") | not) or
      (.shell.panel == "native" or .shell.panel == "omarchy"))
  ' "$profile" >/dev/null
}

frankenstein_effective_shell_profile() {
  local base_profile=$1 override_profile=${2:-}

  frankenstein_validate_base_shell_profile "$base_profile" || {
    echo "Invalid packaged shell profile: $base_profile" >&2
    return 1
  }

  if [[ -z $override_profile || ! -e $override_profile ]]; then
    cat "$base_profile"
    return
  fi

  frankenstein_validate_shell_profile_override "$override_profile" || {
    echo "Invalid KDE shell profile override: $override_profile" >&2
    return 1
  }

  jq -s '
    .[0] as $base |
    .[1] as $override |
    $base * {shell: ($base.shell * $override.shell)}
  ' "$base_profile" "$override_profile"
}
