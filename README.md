# Omarchy Desktop

**Pick a desktop. Give your AI a careful, specific task. Keep your way back.**

A beginner-friendly, read-only desktop chooser and AI prompt generator inspired
by switching between Hyprland and KDE on Omarchy. Includes SDDM diagnosis for the
“it keeps opening the last desktop” problem.

This is an independent community project, not an official Omarchy tool.
Version 0.1 is a prompt generator, not an automatic installer or repair engine.
It never installs packages, edits settings, launches an AI, or changes sessions.

## Try it without installing

Requires Linux and Python 3.10 or newer. No runtime dependencies.
From this project directory:

```sh
python3 -m omarchy_desktop
```

The guided menu lists KDE Plasma, GNOME, Xfce, Cinnamon, COSMIC, LXQt, MATE and
Hyprland. Choose a desktop, then choose **inspect**, **install**, **switch**, or
**recover**. Choose **sddm** for login-screen diagnosis and a repair prompt.
Copy the generated text into your preferred AI assistant.

For a reusable command, install into an isolated environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/omarchy-desktop
```

Activate it with `source .venv/bin/activate` to use the short commands below.
You can also replace `omarchy-desktop` with `python3 -m omarchy_desktop` when
running from the project directory. No administrator access is required.

## Commands

| Command | What it does |
| --- | --- |
| `omarchy-desktop` / `choose` | Guided desktop and task chooser |
| `omarchy-desktop list` | Show detected desktop entries |
| `omarchy-desktop doctor` | Show session and SDDM evidence with findings |
| `omarchy-desktop doctor --json` | Structured evidence for local troubleshooting |
| `omarchy-desktop inspect kde` | Prompt requiring inspection only |
| `omarchy-desktop install gnome` | Prompt to plan an installation, then await approval |
| `omarchy-desktop switch kde` | Prompt for a test login and separately approved default choice |
| `omarchy-desktop recover hyprland` | Prompt to inspect and plan a targeted recovery |
| `omarchy-desktop repair-sddm` | Prompt to diagnose and repair the login screen after approval |

**Install, switch, recover and repair-sddm print prompts. They do not perform
those actions.** The recovery target is your choice; the tool does not know
which desktop last worked and does not keep restore snapshots.

For example, start with `omarchy-desktop inspect kde`, paste the prompt into
Codex, Claude Code, Gemini CLI, OpenCode, Hermes or another agent, and review its
findings. Generate an installation task only when you want a proposed install.
No agent-specific integrations or accounts are required.

## SDDM stuck on the last desktop?

Run:

```sh
omarchy-desktop doctor
omarchy-desktop repair-sddm
```

The repair prompt asks what happens when you select another desktop and tells
your agent to distinguish:

- SDDM remembering the last successful session as configured;
- autologin skipping the chooser;
- a login theme hiding or mishandling session selection;
- a choice not being saved, or a failed session returning to the login screen;
- conflicting settings or obsolete session targets.

The detector reports explicit RememberLastSession settings, differing layered
values, unmatched autologin session filenames, and a Hyprland-based greeter.
These are clues, not confirmed faults. The agent must inspect the installed SDDM
version, remembered state, permissions and logs to diagnose the actual cause.
The tool does not read private SDDM state or journals itself.

Disabling RememberLastSession or deleting state.conf is **not** a universal fix.
The repair prompt requires a minimal diff, backups, a recovery route and your
explicit approval. A greeter that uses Hyprland may still need it while logging
into KDE; switching desktop is not a reason to remove that dependency.

## Safety model

The CLI performs filesystem reads and prints to standard output. It does not
execute discovered session launchers, invoke a shell, request root access, run
package managers, change defaults, disable services or log you out.

Generated tasks require the agent to inspect first, preserve every desktop and
configuration, and wait for explicit confirmation of exact commands and diffs
before **any** system change. Service changes need specific evidence and separate
approval. Restarting the display manager, rebooting or logging out requires
separate confirmation after saving work. Inspect prompts forbid all changes.
The prompts prohibit speculative PAM/keyring changes and configuration resets.

**These are instructions, not a technical sandbox for your AI.** You must review
the agent's plan and permissions. This program cannot enforce how another agent
behaves once you paste a prompt into it.

## What detection means

The tool reads standard system session directories plus SDDM SessionDir overrides.
It reads SDDM fragments in `/usr/lib/sddm/sddm.conf.d`, then `/etc/sddm.conf.d`,
then `/etc/sddm.conf`, retaining setting provenance. It checks the display-manager
symlink, `/usr/share/omarchy/version`, two XDG environment variables, and executable
presence. It reports hidden entries and missing TryExec/Exec launchers.

“Entry detected; login unverified” does **not** mean the desktop is fully installed,
working, or visible in the login screen. Desktop classification is heuristic.
Multiple variants remain visible. Unknown desktops are listed as other entries.
Executable checks use SDDM's configured DefaultPath or common default paths;
wrapper arguments, dependencies and actual launch behavior are not validated.

## Limitations and privacy

- Best-effort Linux/SDDM discovery, not an exhaustive parser or support guarantee.
  Installed build paths, escaped values, custom wrappers and other display managers
  may require manual inspection. Missing configuration means unknown installed defaults.
- An SDDM symlink does not prove it is currently running. UWSM presence does not
  prove it manages your session. Runtime services, packages, logs, user overrides
  and remembered SDDM state must be inspected by the receiving agent.
- Desktop options are prompt targets, not a tested Omarchy compatibility matrix.
  No fixed package lists or recipes are shipped. Omarchy versions differ.
- Detection uses bounded reads and skips malformed/unreadable files with warnings.
  File contents are untrusted evidence. Terminal control characters are escaped.
- Prompts contain local session names, paths, launch commands and selected SDDM
  settings. Review before sharing with a hosted AI. No network requests or
  telemetry are made, and no automatic clipboard or prompt uploads occur.
- This release has fixture tests and a read-only local smoke test; installation,
  switching and graphical recovery have not been tested across desktops or VMs.

## Development and safe tests

```sh
python3 -m unittest discover -s tests -v
python3 -m omarchy_desktop --root /tmp/empty-desktop-fixture doctor --json
```

`--root` must precede the subcommand. It selects a filesystem fixture, ignores
host session environment variables and rejects resolved paths outside that root.
It is a test aid, not a sandbox for adversarial filesystems or concurrent symlink
changes. Tests use temporary files, never the live desktop. CI runs Python 3.10,
3.12 and 3.14, plus package installation and entry-point checks.

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and
[PLAN.md](PLAN.md) for scope and future work.

## References

- [SDDM configuration reference](https://github.com/sddm/sddm/blob/develop/data/man/sddm.conf.rst.in)
- [Desktop Entry Specification](https://specifications.freedesktop.org/desktop-entry/latest-single/)
- [Omarchy source](https://github.com/basecamp/omarchy)
- [UWSM source](https://github.com/Vladimir-csp/uwsm)

Consult the documentation matching the installed versions before changing a system.

## License

[MIT](LICENSE), copyright 2026 transientclover-ui.
