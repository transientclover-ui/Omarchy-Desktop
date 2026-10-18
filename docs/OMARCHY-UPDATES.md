# Omarchy updates and Frankenstein 0.1.0-16

This is a guarded development candidate. It removes the package solver's
unnecessary single-Omarchy-version lock while retaining the exact matching
core/KDE release requirement. **Omarchy 4.0.5 runtime support is not established
by this change. Do not install this candidate until the target-stack checks
and migration review below are complete and the live transition is approved.**

## Why the pin existed

The exact `omarchy=4.0.4-1` dependency was introduced in the first split-package
checkpoint, `1c5ccaa`. The setup script also required exactly that version.
There is no recorded incompatibility with 4.0.5 in that commit: 4.0.4 was the
finite verified development target. There is, however, genuine source coupling:
the package generates a KDE-compatible `Bar.qml` from installed Omarchy source
and links other shell files into its filtered adapter. Removing only the
dependency would leave both the setup restriction and unchecked QML coupling.

Both packages now require `omarchy>=4.0.4`; KDE still requires
`frankenstein-core=0.1.0-16`. Package solvability is separate from permission
to activate an integration. Unknown releases may coexist as packages, without
being declared compatible desktop integrations.

## Compatibility contract

`frankenstein compatibility` (or `frankenstein-compatibility inspect`) is
read-only and reports package versions, candidate series, exact stack validation,
named source capabilities, and source-contract drift. Existing
`frankenstein capabilities` continues to verify live desktop providers and
missing tools independently.

The new policy lives in `src/frankenstein/compatibility/omarchy.json`:

- Candidate releases: Omarchy 4.0.4 and 4.0.5; Plasma 6.7/6.8;
  Qt base and declarative 6.11/6.12; Quickshell 0.3.1/0.3.2.
- Current development stack: Omarchy 4.0.4-1, Plasma workspace 6.7.4-3,
  Qt base 6.11.2-3, Qt declarative 6.11.2-1, Quickshell 0.3.1-1.
  `validated-current` identifies this regression/build baseline; it does not
  claim a newly tested logged-in desktop session or every user widget.
- Named source probes cover shell ping/plugin IPC, registry enablement,
  menu rebuilding, the KDE bar transform, Plasma's Wayland session entry,
  and installed Quickshell QML/IO modules. Presence is not runtime validation.
- A 183-file SHA-256 contract captures the installed 4.0.4 shell source.
  Changed, added or missing files require review. This intentionally errs on
  disabling an unverified adapter, including harmless upstream source edits.
- Compatibility requirements, setup and adoption refuse unknown contracts or
  unvalidated stacks with exit 78. A filtered launch diagnoses the refusal and
  exits normally without launching Quickshell, so existing user-owned services
  with `Restart=on-failure` stay inactive without a restart loop. The new service
  template also prevents restart on exit 78. Automatic watchdog recovery refuses unknown stacks, while
  retaining its diagnostics and ownership checks.
- Preserved Omarchy services, wallpapers, layouts, widget selections and
  user drop-ins retain their existing owners. These checks do not stop the
  preserved shell, replace user helpers, or rewrite configuration. They cannot
  guarantee that upstream Omarchy, Plasma or a third-party widget will preserve
  behavior during its own upgrade.

The known shell digest describes source data, not a script to execute. To add
another supported stack, inspect the actual signed package payloads and changed
hooks/migrations, probe interfaces, build in that complete stack, test in a
disposable Plasma Wayland login, then append a validated stack and (if needed)
another named source contract. Keep prior contracts and rerun their tests.
Do not add a candidate to `validated_stacks` based on version strings alone.
Git-suffixed Quickshell builds are currently unknown, including the alternate
Omarchy repository's `0.3.2.r7.g2b4501a-1` build.

## Validation on 2026-10-18

Actual checks:

- Both split packages built with installed dependencies in bubblewrap. The host
  filesystem was read-only, the checkout writable, HOME temporary, and live
  runtime/service sockets hidden. This is an isolated host-toolchain build,
  **not** a clean chroot with independently installed target dependencies.
- Existing fixture/static regression suites, the actual installed 4.0.4 bar
  transformation, package checksums and metadata were checked. The compiled
  KDE settings module loaded using Qt 6.11/KF 6.29 offscreen, with simulated
  shell status and plugin-list responses.
- A copied local/sync pacman database and a temporary local repository resolve
  **550 packages in one full-system transaction**, including both 0.1.0-16
  packages, Omarchy 4.0.5-1, Plasma workspace 6.8.0-1, Qt base 6.12.0-3,
  Qt declarative 6.12.0-1 and extra/quickshell 0.3.2-1.
  The original database reproduces both exact-pin dependency failures.
  Resolver output is not a transaction, file-conflict check, hook run or migration.

Synthetic checks:

- All 32 combinations of two Omarchy, two Plasma, two Qt base, two Qt
  declarative and two Quickshell versions exercise candidate/validation distinctions. These
  are dictionary fixtures, not installed software combinations. This includes
  mismatched Qt base/declarative families, which remain unvalidated.
- Missing capabilities, missing/unknown versions, source drift, refusal without
  file changes, and watchdog refusal are covered by regression tests.

Blocked or untested:

- Installer rollback and preservation lifecycle tests require a network
  namespace; this environment denies bubblewrap's NETLINK_ROUTE socket.
  One desktop-capability test cannot bind its synthetic Unix sockets.
  The two lifecycle suites also passed using an explicitly selected alternate
  bubblewrap runner with private user/PID/IPC/UTS namespaces, read-only host,
  writable fixtures and hidden `/run`, without a network namespace. All
  package/service calls were simulated; the platform's socket restrictions
  still applied. This does not establish network isolation by that runner.
- The isolated offscreen Quickshell attempt could not open IPC and had no
  PanelWindow backend. It is not a QML runtime pass or a discovered regression
  in a real Plasma Wayland session.
- No target packages were cached. Network DNS fails and web retrieval is
  disabled. Consequently 4.0.5 source, install scripts, hooks, migrations,
  Plasma 6.8, Qt 6.12 and Quickshell 0.3.2 were not executed or validated.
  The filtered adapter and automatic recovery stay disabled on that stack.
- No installation, system upgrade, desktop restart, configuration migration or
  new graphical login occurred on the host.

## Proposed coordinated transition — approval required

The commands below are a reviewable plan, **not authorization to run them**.
First restore network access, verify the live remote/experimental branch, obtain
and verify the target package payloads, audit their hooks/migrations, and finish
the missing tests in a disposable complete target system. Regenerate the full
resolver plan against then-current databases. Stop on unreviewed replacements,
removals, ignored packages, new conflicts or new source drift.

Do not use `install-frankenstein.sh` to repair this already-installed pair: it
updates first and cannot break the old pin cycle. Do not run setup or adoption
on this desktop. Use a temporary, local sync repository so the **normal
`omarchy update` transaction upgrades the pair and the whole system together**.
No `--nodeps`, removals, `--assume-installed`, forced dependencies or selective
Plasma/Qt/Omarchy upgrade is needed.

### Backup before staging the transition

After approval, save work and use a terminal where the full update can finish.
Use a persistent backup directory on `/home`, which is a separate Btrfs
subvolume and is not included by the root snapshot:

```bash
backup="$HOME/frankenstein-before-0.1.0-16-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 "$backup"
pacman -Q > "$backup/packages.txt"
pacman -Qqe > "$backup/explicit-packages.txt"
pacman -Qu > "$backup/pending-packages.txt"
paths=()
for item in .config .local/bin .local/state/frankenstein .local/state/omarchy \
  .local/share/plasma .local/share/omarchy .local/share/wallpapers \
  .local/share/color-schemes .local/share/icons; do
  [[ ! -e "$HOME/$item" && ! -L "$HOME/$item" ]] || paths+=("$item")
done
tar --acls --xattrs -C "$HOME" -cpf "$backup/desktop.tar" "${paths[@]}"
# Preserve the external wallpaper currently referenced by Plasma as well.
cp --preserve=all -- \
  "$HOME/Downloads/Wallpapers/Warframe/GfQi7P8WkAA92kC.jpg" "$backup/"
sudo tar --acls --xattrs --numeric-owner -C / -cpf "$backup/system-config.tar" \
  etc var/lib/frankenstein var/lib/pacman/local
sudo tar --numeric-owner -C /boot -cpf "$backup/boot.tar" .
sudo cp --preserve=all /etc/pacman.conf "$backup/pacman.conf"
sudo snapper -c root create --read-only --print-number \
  --description 'Before Frankenstein coordinated upgrade' > "$backup/root-snapshot-id"
cat "$backup/root-snapshot-id"
tar -tf "$backup/desktop.tar" >/dev/null
sudo tar -tf "$backup/system-config.tar" >/dev/null
sudo tar -tf "$backup/boot.tar" >/dev/null
```

Retain the original **both** 0.1.0-15 archives from
`/home/violet/Documents/Codex/2026-10-12/referenced-chatgpt-conversation-this-is-an-5/outputs/dogfood-update/`
in this backup, plus the complete downloaded old-package cache if available.
The root snapshot is essential because not all old repository packages are
cached. `/boot` and `/home` need their separate backups. Verify recovery boot
entries and available space before proceeding; a snapshot alone is not a
verified recovery procedure. The full update also creates/prunes its own
snapshots, so retain the explicit snapshot number and avoid subsequent updates
until acceptance testing is complete.

### Stage the exact local pair, then run the supported full update

Set `candidate` to the reviewed directory containing the two packages,
`frankenstein-transition.db.tar.gz`, `frankenstein-transition.files.tar.gz`
and `SHA256SUMS`. Verify hashes against the delivered manifest first:

```bash
cd "$candidate"
sha256sum -c SHA256SUMS
sudo install -d -m 0755 /var/lib/frankenstein/transition-0.1.0-16
sudo install -m 0644 -- ./*.pkg.tar.zst \
  frankenstein-transition.db.tar.gz frankenstein-transition.files.tar.gz \
  SHA256SUMS /var/lib/frankenstein/transition-0.1.0-16/
sudo ln -s frankenstein-transition.db.tar.gz \
  /var/lib/frankenstein/transition-0.1.0-16/frankenstein-transition.db
sudo ln -s frankenstein-transition.files.tar.gz \
  /var/lib/frankenstein/transition-0.1.0-16/frankenstein-transition.files
test ! -e /etc/pacman.d/frankenstein-transition.conf || exit 1
sudo tee /etc/pacman.d/frankenstein-transition.conf >/dev/null <<'EOF'
[frankenstein-transition]
SigLevel = Optional
Server = file:///var/lib/frankenstein/transition-0.1.0-16
EOF
printf '\nInclude = /etc/pacman.d/frankenstein-transition.conf\n' | \
  sudo tee -a /etc/pacman.conf >/dev/null
omarchy update
```

`SigLevel=Optional` applies only to these hash-reviewed, unsigned local builds;
it does not change remote repository signature requirements. The local repository
must contain exactly the reviewed pair. A signed production repository is the
preferred long-term delivery mechanism, but none is configured on this host.

Do not refresh live package databases separately. Let the supported Omarchy
entrypoint manage its update lock, keyring, complete transaction, snapshot,
migrations, post-update hooks, AUR/mise phases and restart handling. Do not set
`OMARCHY_ALLOW_DIRECT_PACMAN` or impersonate its update-entrypoint environment.
The inspected 4.0.4 updater uses its own `/usr/share/omarchy/*` overwrite policy;
that is upstream behavior, not a new Frankenstein dependency bypass.

The full upgrade can invoke locale/cache rebuilds, system/user daemon-reload,
udev and marked-service actions, initramfs/kernel/firmware hooks, Limine EFI
deployment and Hyprland reload guards. Omarchy migrations and post-update hooks
can change user configuration; the update's final phase may restart the shell
or offer a reboot. These are reasons the whole transition requires approval.
The target payload must be audited before claiming exact effects. Do not promise
an uninterrupted desktop during this 550-package upgrade.

If the package transaction fails, stop and preserve its log; do not run
migrations manually or try a smaller package subset. If hooks or migrations
fail after packages have changed, treat the system as upgraded-but-incomplete,
retain logs, and diagnose or use the coordinated rollback below.

### Verify and accept

After the approved update and an approved normal reboot/login boundary:

```bash
pacman -Q frankenstein-core frankenstein-kde omarchy plasma-workspace \
  qt6-base qt6-declarative quickshell
pacman -Qkk frankenstein-core frankenstein-kde
frankenstein compatibility
frankenstein inspect
frankenstein doctor --json
frankenstein check
systemctl --user status omarchy-shell.service --no-pager
systemctl --user cat omarchy-shell.service
journalctl --user -b -u omarchy-shell.service -u frankenstein-watchdog.service --no-pager
omarchy-migrate --pending
```

`omarchy-migrate --pending` returns 1 when there are no pending entries.
Confirm exactly one intended shell, Plasma Wayland, unchanged wallpaper and
panel layout, all chosen widgets, settings visibility, restart routing and
the original service drop-ins. Compare configuration backups and explain
every migration change before accepting it. Test display sleep/wake and normal
login/logout in the disposable target environment before risking the live setup.
Do not use a disabled filtered adapter's report as evidence that the preserved
stock shell has failed.

After acceptance, remove only the exact temporary Include line and its generated
configuration file; retain package archives and logs:

```bash
sudo sed -i '\|^Include = /etc/pacman.d/frankenstein-transition.conf$|d' /etc/pacman.conf
sudo rm /etc/pacman.d/frankenstein-transition.conf
```

### Coordinated rollback

Do not downgrade only Omarchy, Plasma, Qt, Quickshell or Frankenstein. The old
Frankenstein pair requires Omarchy 4.0.4-1; restoring only those two archives on
4.0.5 is invalid. Restore the pre-update root (including `/usr`, `/etc` and the
pacman local database) together with its matching boot artifacts and user state.

1. Stop further updates. Save update, migration and journal logs outside root.
   Save any newly created user work before restoring the home configuration.
2. Reboot to the recorded pre-update snapshot through the inspected Limine
   snapshot menu. From that snapshot, run `sudo limine-snapper-restore` and
   follow its restore prompts. Its normal mode is intended to run while booted
   in the selected snapshot; do not pass an invented snapshot-ID positional arg.
3. Verify matching kernel/initramfs/EFI artifacts. The installed tool supports
   `sudo limine-snapper-restore --kernels ID` for kernel recovery, but review its
   output before use. The saved `/boot` archive is recovery evidence and a
   fallback for a rescue environment; do not extract it over a running boot
   filesystem without checking that it belongs to the restored root.
4. While logged out of Plasma (TTY/rescue), quarantine the current affected
   home configuration and restore `desktop.tar` to `/home/violet` under violet's
   ownership. Restore the separately saved wallpaper only if it changed.
   Do not overlay old state while Plasma/Quickshell is writing it. Do not copy
   the pacman database alone from `system-config.tar` onto newer installed files.
5. Reboot normally. Verify the original 0.1.0-15 pair, Omarchy 4.0.4-1,
   Plasma 6.7.4, Qt 6.11.2, Quickshell 0.3.1 and the saved desktop/service
   hashes. Diagnose any differences before resuming updates.

The exact recovery menu and restoration must be rehearsed in a disposable
system before live approval. No rollback or live backup was executed here.

## Future Frankenstein delivery

Pushing `experimental/kde-omarchy-bar` delivers source only. This host has no
Frankenstein package repository and will not discover new builds automatically.
Until a signed repository is published and explicitly configured, each update
requires rebuilding both matching packages, reviewing hashes/tests and making
them available to the next normal full-system transaction. Keep the pair's
versions coordinated. The repository's existing signing/publishing scripts in
`packaging/repository/` provide the production path; signing keys, hosting and
trust configuration are separate deployment work. No automatic updater,
repository configuration or key trust was installed by this task.
