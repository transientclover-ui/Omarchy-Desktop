# Contributing

Keep discovery read-only and usable with Python's standard library. Add fixture
coverage for safety-relevant changes. Do not add commands that install packages,
reset configuration, disable services or execute .desktop entries.

For bug reports, include the tool version, Omarchy/SDDM versions and a sanitized
reproduction. Review diagnostic output for private paths and commands before
posting. Never upload authentication data or unredacted journals.

Test with `python3 -m unittest discover -s tests -v`. Use throwaway filesystem
fixtures or disposable VMs for integration work. Do not test login changes on a
contributor's working desktop. Document the exact VM/image version for any
compatibility claim.

Prompt changes must retain inspect-only behavior, explicit approval before
changes, targeted backups and rollback, preservation of desktops and separate
approval for session interruption. A future mutation engine would need its own
design review and cannot be introduced as a small convenience flag.
