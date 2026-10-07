# Omarchy Shell in KDE System Settings

Open **System Settings → Workspace → General Behavior → Omarchy Shell**,
or search System Settings for **Omarchy Shell**. It can also be opened directly:

```
systemsettings kcm_frankenstein_shell
```

The Enable Omarchy shell checkbox takes effect immediately. For a preserved
installation it enables/disables the existing `omarchy-shell.service` and starts
or stops it, so the preference persists across logins. For a filtered installation
it uses the existing Frankenstein adapter enable/disable controls and marker.
The toggle does not reset shell.json or change Plasma panels, widgets or KWin.

When the preserved shell is running, the page lists discovered widgets and
plugins. Check or uncheck an item to invoke the existing `omarchy plugin enable`
or `omarchy plugin disable` command. Both enabled and disabled items are shown;
non-disableable infrastructure is excluded. Omarchy handles widget placement and
configuration changes. Disabling a plugin may remove its corresponding layout
entries according to Omarchy's existing behavior. The page does not install,
update or remove plugin code. Refresh reloads status and the list.

Widget selection for the filtered adapter remains profile-managed and is
identified as such in the page. No stock widget controls are offered for that
adapter. Enabling the shell may briefly require Refresh while IPC initializes.

CLI equivalents:

```
frankenstein shell on
frankenstein shell off
frankenstein shell status
```

The KDE module and launcher are package-owned; upgrade replaces them and package
removal/rollback removes them. Explicit user enable/disable choices belong to the
user's existing shell service, rather than package installation hooks.

Verification includes mocked shell-control tests and a read-only KDE module
smoke test in `tests/kcm-smoke.cpp` that loads the plugin, verifies the enabled
shell and nonempty selectable list, and optionally saves a rendering. This smoke
test assumes a running, recorded preserved shell and never clicks controls.
