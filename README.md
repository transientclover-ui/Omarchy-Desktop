# Omarchy Desktop — Omarchy desktop compatibility

**Choose your desktop. Keep Omarchy shell.**

Omarchy Desktop is an independent Omarchy desktop compatibility/adoption project,
not an official Omarchy tool. The goal is freedom to choose another desktop
while retaining a desktop-appropriate Omarchy shell experience. It explores
Omarchy desktop adoption, KDE Plasma integration and safe desktop switching.

This repository provides a beginner-friendly, read-only desktop chooser and AI
prompt generator, including SDDM diagnosis for the “it keeps opening the last
desktop” problem. The current Python CLI (0.2) is a prompt generator, not an
automatic installer or repair engine.
It never installs packages, edits settings, launches an AI, or changes sessions.

The public repository is [transientclover-ui/Omarchy-Desktop](https://github.com/transientclover-ui/Omarchy-Desktop).
The Python package/module `omarchy_desktop`, distribution name `omarchy-desktop`,
and CLI command `omarchy-desktop` remain stable for compatibility.

## Try it without installing

Requires Linux and Python 3.10 or newer. No runtime dependencies.
From this project directory:

```sh
python3 -m omarchy_desktop
```

The guided menu lists KDE Plasma, GNOME, Xfce, Cinnamon, COSMIC, LXQt, MATE and
Hyprland, plus Budgie, Deepin, LXDE, Enlightenment, Sway, Niri, i3 and Openbox.
These are candidates, not verified recommendations. Choose a desktop, then
**inspect**, **verify**, **install**, **switch**, or **recover**. Choose **sddm** for login-screen diagnosis and a repair prompt.
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

## Omarchy shell stays on by default

Validated installation/switch plans must keep Omarchy shell enabled and preserve
its configuration. Users can choose to disable it later in a separate explicit
task. The tool does not turn it off to work around compatibility problems.

**The CLI has no registered exact-version compatibility reports.** Install/switch
requests therefore still generate inspection-only prompts for every candidate,
including KDE and Hyprland. The VM work below does not automatically satisfy
this CLI's full shell checklist or change its compatibility gate.

### Validation status

The [compatibility journal](COMPATIBILITY-JOURNAL.md) records completed VM work
on Omarchy 4.0.4 with KDE Plasma, including graphical logins and native logout
cycles between Plasma and Omarchy, SDDM selection/default behavior, and a filtered
Omarchy menu profile under Plasma. Plasma retained its native panel, lock/idle,
notifications, Polkit agent, wallpaper, workspaces and OSD; this was not full
stock-shell support under Plasma. Package upgrade, downgrade, uninstall/removal,
reproducible builds, and a VM-only signed repository install/update were also
validated at the recorded revisions (0.1.0-2 and signed update 0.1.0-4).

That adoption implementation lives in the separate VM work checkout; it is not
installed by this Python package. The journal is included here as an evidence
snapshot, with its checkout and artifact provenance explained at the top.
GNOME and other desktop profiles were not implemented or tested there.

**Later partial host-adoption work remains unvalidated for release.** Local
shell-profile and simulated-service rollback tests passed, but broader review,
restoration-failure coverage, package metadata/checksum/revision updates,
reproducible builds and fresh disposable-VM validation remain pending. Those
local passes do not establish real-systemd/SDDM behavior, standalone-install
parity, or non-menu shell compatibility. No host installation is authorized.

Run `omarchy-desktop compatibility` to see evidence status and
`omarchy-desktop verify kde` for a safe test-planning prompt. See the
[compatibility matrix and process](compatibility/README.md). This restriction is
intentional: the chooser should recommend combinations shown to work well.

## Commands

| Command | What it does |
| --- | --- |
| `omarchy-desktop` / `choose` | Guided desktop and task chooser |
| `omarchy-desktop compatibility` | Show version-specific shell compatibility status |
| `omarchy-desktop verify kde` | Prepare a disposable-system integration test plan |
| `omarchy-desktop list` | Show detected desktop entries |
| `omarchy-desktop doctor` | Show session and SDDM evidence with findings |
| `omarchy-desktop doctor --json` | Structured evidence for local troubleshooting |
| `omarchy-desktop inspect kde` | Prompt requiring inspection only |
| `omarchy-desktop install gnome` | Inspection only unless shell compatibility is verified; then plan and await approval |
| `omarchy-desktop switch kde` | Inspection only unless verified; then plan a test login and approved default choice |
| `omarchy-desktop recover hyprland` | Prompt to inspect and plan a targeted recovery |
| `omarchy-desktop repair-sddm` | Prompt to diagnose and repair the login screen after approval |

**Install, switch, recover and repair-sddm print prompts. They do not perform
those actions.** The recovery target is your choice; the tool does not know
which desktop last worked and does not keep restore snapshots.

For example, start with `omarchy-desktop inspect kde`, paste the prompt into
Codex, Claude Code, Gemini CLI, OpenCode, Hermes or another agent, and review its
findings. Installation planning becomes available only after a reviewed,
version-matched shell compatibility report is registered.
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
- This Python CLI has fixture tests and a read-only local smoke test. The
  journal records separate, bounded KDE/Omarchy VM integration work; it does not
  establish arbitrary desktop, version, hardware or graphical-recovery support.

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
