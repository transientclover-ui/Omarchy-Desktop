# Validation for 0.1.0

Local validation completed on 2026-09-22 with Python 3.14:

- 16 temporary-fixture tests passed.
- Built and installed the package in an isolated virtual environment.
- Installed command returned version 0.1.0 and generated an SDDM repair prompt.
- Installed command ran from outside the source tree against an empty fixture.
- Read-only local session discovery recognized KDE and Hyprland entries.
- Staged files passed whitespace checks.

Tests cover configuration precedence, custom session directories, hidden/broken
entries, malformed/oversized files, fixture symlink containment, no subprocess
execution or fixture modification, terminal escaping, JSON, menu paths, argument
validation and prompt approval requirements.

The GitHub Actions matrix is prepared but has not run remotely. No desktop
installation, graphical login, default change or SDDM repair was performed.
No cross-version or multi-desktop compatibility claim is made.

## Version 0.2 validation

21 local fixture/unit tests pass, including the compatibility gate, exact-version
matching, broader candidate commands and shell-enabled-by-default prompts.
No graphical desktop compatibility is certified. Version 0.1's GitHub matrix
passed on Python 3.10, 3.12 and 3.14 after publication.
