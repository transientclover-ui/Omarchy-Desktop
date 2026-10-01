# Agent-readable SDDM state

Frankenstein writes non-sensitive operational evidence to:

```text
${XDG_STATE_HOME:-~/.local/state}/frankenstein/sddm-state.json
```

The file is UTF-8 JSON, written atomically, and has `schema_version: 1`.
Diagnostic agents may read it directly, but must treat it as evidence rather
than authority. `frankenstein doctor` compares it with effective SDDM
configuration, installed theme files, staged backgrounds, and detected session
entries.

## Schema

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | integer | State schema; currently `1` |
| `frankenstein_version` | string | CLI/package version that wrote the file |
| `theme_version` | string | Frankenstein SDDM theme version |
| `theme_installed` | boolean | Last observed payload installation state |
| `theme_active` | boolean | Last observed effective SDDM theme state |
| `selected_background` | string | Last selected bundled or staged path |
| `default_background` | string | Packaged fallback path |
| `last_known_valid_background` | string or null | Last successfully validated path |
| `sddm_configuration_path` | string or null | Managed SDDM fragment, if known |
| `previous_theme` | string or null | Theme observed before an approved switch |
| `backup_location` | string or null | Recovery backup associated with the switch |
| `detected_sessions` | array of strings | Session IDs observed during validation |
| `last_validation` | object | Writer version and UTC timestamp |

Unknown fields and unsupported schema versions are reported rather than
silently accepted. Absent, malformed, stale, symlinked, or non-regular state is
non-fatal diagnostic evidence and never triggers an automatic repair.

The greeter separately persists its staged-image choice under the SDDM
greeter's own `~/.config/frankenstein/` directory. That setting contains only a
path from the fixed bundled/staged collection. It does not contain credentials
and does not grant access to user homes. The post-login importer updates the
user JSON after a successful staged import.

The state file must never contain passwords, usernames unless a future
operational requirement is separately reviewed, tokens, cookies, credentials,
private authentication material, network URLs, or unrelated personal data.
