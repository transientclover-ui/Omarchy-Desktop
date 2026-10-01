#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT
"""Run real packaged and standalone setup/uninstall in bubblewrap with simulated system services.

Requires Linux user namespaces, bwrap, Python 3, bash, and jq. Never falls back
outside the sandbox. The host filesystem is read-only; only temporary fixtures
are writable. No root privileges, package transactions, or real services run.
"""
import os
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import tarfile

PROJECT = Path(__file__).resolve().parents[1]


def put(root, name, text, executable=False):
    path = root / name.lstrip('/')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if executable:
        path.chmod(0o755)
    return path


def copy(root, source, destination):
    target = root / destination.lstrip('/')
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        target.unlink()
    shutil.copy2(PROJECT / source, target)


def fixture(root, existed, standalone=False):
    # Expose executable/library dependencies through read-only host mounts.
    # Dedicated bin and lib directories let the packaged layout be populated
    # without overlaying or writing any host installation paths.
    for directory in ('bin', 'lib'):
        target = root / 'usr' / directory
        target.mkdir(parents=True)
        for entry in (Path('/usr') / directory).iterdir():
            if entry.name not in ('frankenstein', 'systemd'):
                (target / entry.name).symlink_to('/mnt/' + directory + '/' + entry.name)
    for directory in ('etc/sddm.conf.d', 'var/lib/sddm', 'home/test',
                      'usr/local', 'usr/share', 'usr/lib/systemd/system', 'mock'):
        (root / directory).mkdir(parents=True, exist_ok=True)
    put(root, 'etc/os-release', 'ID=arch\n')
    put(root, 'etc/sddm.conf.d/original.conf', '[Theme]\nCurrent=omarchy\n')
    for session in ('omarchy', 'plasma'):
        put(root, f'usr/share/wayland-sessions/{session}.desktop',
            f'[Desktop Entry]\nType=Application\nName={session}\nExec=/usr/bin/true\n')
    for name, content in {
        'shell.qml': 'property PluginRegistry pluginRegistry',
        'services/PluginRegistry.qml': 'function isEnabled(id)',
        'plugins/menu/Menu.qml': 'function rebuildItemsFromSources()',
        'plugins/bar/Bar.qml': '''import Quickshell
import Quickshell.Hyprland
Item {
  function focusedScreenName() {
    var monitor = Hyprland.focusedMonitor
    return monitor ? String(monitor.name || "") : ""
  }
}
''',
    }.items():
        put(root, 'usr/share/omarchy/shell/' + name, content + '\n')
    for source, destination in {
        'install.sh': 'usr/lib/frankenstein/setup',
        'uninstall.sh': 'usr/lib/frankenstein/uninstall',
        'src/lib/installer-state.sh': 'usr/lib/frankenstein/installer-state',
        'src/lib/shell-profile.sh': 'usr/lib/frankenstein/shell-profile',
        'src/libexec/frankenstein-state': 'usr/lib/frankenstein/state',
        'src/libexec/frankenstein-diagnostics': 'usr/lib/frankenstein/diagnostics',
        'src/libexec/frankenstein-adopt-kde-shell': 'usr/lib/frankenstein/adopt-kde-shell',
        'src/libexec/frankenstein-sddm-validate': 'usr/lib/frankenstein/sddm-validate',
        'src/bin/frankenstein-shell-adapter': 'usr/bin/frankenstein-shell-adapter',
        'src/bin/frankenstein-settings': 'usr/bin/frankenstein-settings',
        'src/bin/frankenstein-kde-soft-defaults': 'usr/bin/frankenstein-kde-soft-defaults',
        'src/bin/frankenstein-background': 'usr/bin/frankenstein-background',
        'src/libexec/frankenstein-background-writer': 'usr/libexec/frankenstein-background-writer',
        'src/bin/omarchy-default-desktop': 'usr/bin/omarchy-default-desktop',
        'src/frankenstein/plasma-shell-profile.json': 'usr/share/frankenstein/profiles/plasma.json',
        'src/frankenstein/plasma-menu.jsonc': 'usr/share/frankenstein/profiles/plasma-menu.jsonc',
        'src/frankenstein/presets/dusk-9x.json': 'usr/share/frankenstein/presets/dusk-9x.json',
        'src/frankenstein/themes/dusk/FrankensteinDusk.colors': 'usr/share/color-schemes/FrankensteinDusk.colors',
        'src/frankenstein/themes/dusk/colors.toml': 'usr/share/frankenstein/themes/dusk/colors.toml',
        'src/frankenstein/themes/dusk/shell.toml': 'usr/share/frankenstein/themes/dusk/shell.toml',
        'src/frankenstein/themes/dusk/wallpaper/metadata.json': 'usr/share/wallpapers/FrankensteinDusk/metadata.json',
        'src/frankenstein/zzzz-frankenstein.conf': 'usr/share/frankenstein/templates/zzzz-omarchy-desktop-manager.conf',
        'src/sddm/frankenstein/Main.qml': 'usr/share/sddm/themes/frankenstein/Main.qml',
        'src/sddm/frankenstein/metadata.desktop': 'usr/share/sddm/themes/frankenstein/metadata.desktop',
        'src/sddm/frankenstein/theme.conf': 'usr/share/sddm/themes/frankenstein/theme.conf',
        'src/sddm/frankenstein/backgrounds/vaporwave-default.png': 'usr/share/wallpapers/FrankensteinDusk/contents/images/1672x941.png',
        'src/frankenstein/frankenstein-omarchy-shell-autostart.desktop': 'usr/share/frankenstein/templates/frankenstein-omarchy-shell.desktop',
        'src/frankenstein/frankenstein-kde-soft-defaults.desktop': 'usr/share/frankenstein/templates/frankenstein-kde-soft-defaults.desktop',
        'src/frankenstein/frankenstein-omarchy-menu.desktop': 'usr/share/frankenstein/templates/frankenstein-omarchy-menu.desktop',
        'src/systemd/frankenstein-omarchy-shell.service': 'usr/share/frankenstein/templates/frankenstein-omarchy-shell.service',
    }.items():
        copy(root, source, destination)
    copy(root, 'src/sddm/frankenstein/backgrounds/vaporwave-default.png',
         'usr/share/sddm/themes/frankenstein/backgrounds/vaporwave-default.png')
    for role in ('left_ptr', 'hand2', 'xterm', 'watch', 'left_ptr_watch'):
        put(root, 'usr/share/icons/whiteglass/cursors/' + role,
            'fixture XCursor data\n')
    for unit in ('path', 'service'):
        name = 'omarchy-desktop-manager-default.' + unit
        copy(root, 'src/systemd/' + name, 'usr/lib/systemd/system/' + name)
    for name in ('shell.qml', 'services/PluginRegistry.qml', 'plugins/menu/Menu.qml'):
        copy(root, 'src/frankenstein/omarchy-shell/' + name,
             'usr/share/frankenstein/omarchy-shell/' + name)
    put(root, 'usr/share/frankenstein/omarchy-shell/plugins/bar/Bar.qml',
        'import Quickshell\nItem { function focusedScreenName() { return "" } }\n')
    state = root / 'var/lib/sddm/state.conf'
    if existed:
        state.write_text('[Last]\nSession=original.desktop\nUser=original\n')
        state.chmod(0o640)
        os.utime(state, (1700000000, 1700000000))
    put(root, 'mock/pacman', '''#!/bin/bash
case "$*" in
  '-Q omarchy') echo 'omarchy 4.0.4-1';;
  '-Q frankenstein-core'|'-Q frankenstein-kde') [[ ${STANDALONE:-0} == 0 ]];;
  '-Qq') printf '%s\\n' omarchy frankenstein-core frankenstein-kde;;
  *) exit 90;;
esac
''', True)
    put(root, 'mock/sudo', '''#!/bin/bash
[[ $1 == -v ]] && exit 0
[[ $1 == -n && $2 == true ]] && exit 0
if [[ $1 == /usr/lib/frankenstein/set-default ]]; then
  shift
  exec /opt/set-default "$@"
fi
# Every restore must occur after both simulated systemd units stop.
case "$1:$*" in
  mv:*state.conf*|rm:*sddm/state.conf*)
    if [[ -e /var/path-active || -e /var/sync-active ]]; then
      echo 'RESTORE WHILE SYNCHRONIZATION ACTIVE' >&2
      exit 91
    fi;;
esac
case "${FAIL_RESTORE:-}:$1:$*" in
  directory:install:*"-m 0755 /var/lib/sddm"|temporary:mktemp:*/var/lib/sddm/.state.conf.frankenstein.*)
    echo 'INJECTED SDDM RESTORE FAILURE' >&2
    exit 44;;
  rename:mv:*sddm/state.conf*|remove:rm:*sddm/state.conf*|copy:cp:*--preserve=all*)
    echo 'INJECTED SDDM RESTORE FAILURE' >&2
    exit 44;;
esac
exec "$@"
''', True)
    put(root, 'mock/systemctl', '''#!/bin/bash
case "$*" in
  '--user show omarchy-shell.service -p LoadState --value')
    if [[ -f /home/test/.config/systemd/user/omarchy-shell.service ]]; then echo loaded; else echo not-found; fi
    exit 0;;
  '--user is-enabled omarchy-shell.service')
    [[ -L /home/test/.config/systemd/user/graphical-session.target.wants/omarchy-shell.service ]] && { echo enabled; exit 0; }
    echo disabled; exit 1;;
  '--user is-active omarchy-shell.service')
    [[ -e /var/original-shell-active ]] && { echo active; exit 0; }
    echo inactive; exit 3;;
  '--user is-active frankenstein-omarchy-shell.service')
    echo active; exit 0;;
esac
printf '%s\\n' "$*" >>/var/service-calls
case "$*" in
  'enable --now omarchy-desktop-manager-default.path')
    touch /var/path-active
    [[ ${FAIL_WATCH:-0} == 1 ]] && exit 42;;
  'disable --now omarchy-desktop-manager-default.path')
    [[ ${FAIL_STOP:-} == path ]] && exit 43
    rm -f /var/path-active;;
  'stop omarchy-desktop-manager-default.service')
    [[ ${FAIL_STOP:-} == service ]] && exit 43
    rm -f /var/sync-active;;
  '--user disable --now omarchy-shell.service')
    rm -f /home/test/.config/systemd/user/graphical-session.target.wants/omarchy-shell.service /var/original-shell-active;;
  '--user enable omarchy-shell.service')
    mkdir -p /home/test/.config/systemd/user/graphical-session.target.wants
    ln -sfn ../omarchy-shell.service /home/test/.config/systemd/user/graphical-session.target.wants/omarchy-shell.service;;
  '--user start omarchy-shell.service') touch /var/original-shell-active;;
  '--user start frankenstein-omarchy-shell.service')
    [[ ${FAIL_SETUP:-0} == 1 ]] && exit 42;;
  '--user restart frankenstein-omarchy-shell.service')
    [[ ${FAIL_SETUP:-0} == 1 ]] && exit 42;;
  '--user daemon-reload'|'--user stop frankenstein-omarchy-shell.service'|'daemon-reload') ;;
  *) echo "Unexpected service call: $*" >&2; exit 92;;
esac
exit 0
''', True)
    put(root, 'usr/lib/frankenstein/set-default', '''#!/bin/bash
printf '[Last]\\nSession=changed.desktop\\n' >/var/lib/sddm/state.conf
touch /var/sync-active
mkdir -p /var/lib/omarchy-desktop-manager
echo "$1" >/var/lib/omarchy-desktop-manager/default-session
[[ ${FAIL_DEFAULT:-0} == 1 ]] && exit 42
exit 0
''', True)
    shutil.copy2(root / 'usr/lib/frankenstein/set-default', root / 'mock/set-default')
    put(root, 'mock/pgrep', '''#!/bin/bash
case "$*" in
  *'quickshell -n -p /usr/share/frankenstein/omarchy-shell'*) echo 1;;
  *'polkit'*|*'polkit-kde-authentication-agent'*) echo 1;;
  *) exit 1;;
esac
''', True)
    put(root, 'mock/qs', '''#!/bin/bash
case "$*" in
  *' call -- shell ping') echo ok;;
  *' call -- shell listPlugins') echo '[]';;
  *' call -- shell barStatus')
    panel=$(jq -r '.shell.panel // "native"' \
      /home/test/.config/frankenstein/plasma.json 2>/dev/null || echo native)
    if [[ $panel == omarchy ]]; then
      echo '{"loaded":true,"hidden":false}'
    else
      echo '{"loaded":false,"hidden":false}'
    fi;;
  *) exit 93;;
esac
''', True)
    for name in ('quickshell', 'systemsettings', 'xdg-terminal-exec', 'qdbus6',
                 'plasma-apply-colorscheme', 'plasma-apply-wallpaperimage'):
        put(root, 'mock/' + name, '#!/bin/bash\nexit 93\n', True)

    validator = '''#!/bin/bash
echo validate-sddm >>/var/operation-order
[[ ${FAIL_SDDM_VALIDATION:-0} == 0 ]] || {
  echo 'INJECTED SDDM VALIDATION FAILURE' >&2
  exit 46
}
'''
    put(root, 'usr/lib/frankenstein/sddm-validate', validator, True)

    for name in ('kdeglobals', 'plasmarc', 'kwinoutputconfig.json', 'ksmserverrc',
                 'powermanagementprofilesrc', 'Trolltech.conf',
                 'plasma-org.kde.plasma.desktop-appletsrc'):
        put(root, 'home/test/.config/' + name, 'original KDE configuration: ' + name + '\n')
    put(root, 'home/test/.config/kdeglobals',
        '[General]\nColorScheme=Custom\n[KDE]\nwidgetStyle=Breeze\n[Icons]\nTheme=Custom\n')
    put(root, 'home/test/.config/kcminputrc', '[Mouse]\ncursorTheme=Custom\n')
    put(root, 'home/test/.config/plasma-org.kde.plasma.desktop-appletsrc',
        '[Containments][1][Wallpaper]\nwallpaperplugin=org.kde.image\nImage=file:///custom.png\n')
    put(root, 'home/test/.local/share/plasma/look-and-feel/custom/metadata.json',
        '{"KPlugin": {"Id": "custom"}}\n')
    put(root, 'home/test/.local/share/color-schemes/custom.colors',
        '[General]\nName=Custom\n')
    put(root, 'home/test/.local/share/icons/custom/index.theme',
        '[Icon Theme]\nName=Custom\n')
    if standalone:
        shutil.rmtree(root / 'usr/lib/frankenstein')
        shutil.rmtree(root / 'usr/share/frankenstein')
        shutil.rmtree(root / 'usr/lib/systemd/system')
        (root / 'usr/lib/systemd/system').mkdir()
        for name in (
            'frankenstein-shell-adapter',
            'omarchy-default-desktop',
            'frankenstein-settings',
            'frankenstein-kde-soft-defaults',
            'frankenstein-background',
        ):
            (root / 'usr/bin' / name).unlink()
        (root / 'usr/libexec/frankenstein-background-writer').unlink()
        shutil.rmtree(root / 'usr/share/sddm/themes/frankenstein')
        shutil.copytree(PROJECT / 'src', root / 'home/source/src')
        put(root, 'home/source/src/libexec/frankenstein-sddm-validate', validator, True)
        for name in ('install.sh', 'uninstall.sh'):
            copy(root, name, 'home/source/' + name)


def run(root, script, fail=False, fail_stop="", fail_restore="", preflight=False,
        fail_default=False, fail_watch=False, fail_sddm_validation=False, arguments=None):
    standalone = (root / 'home/source').exists()
    entry = ('/usr/bin/frankenstein-shell-adapter' if script == 'adapter' else
             '/usr/lib/frankenstein/adopt-kde-shell' if script == 'migration' else
             '/home/source/' + script if standalone else
             '/usr/lib/frankenstein/' + {'install.sh': 'setup', 'uninstall.sh': 'uninstall'}[script])
    command = ['bwrap', '--ro-bind', '/', '/', '--unshare-all', '--die-with-parent',
               '--ro-bind', '/usr', '/mnt', '--bind', str(root / 'usr'), '/usr',
               '--bind', str(root / 'etc'), '/etc', '--bind', str(root / 'var'), '/var',
               '--bind', str(root / 'home'), '/home', '--ro-bind', str(root / 'mock'), '/opt',
               '--tmpfs', '/tmp', '--proc', '/proc', '--dev', '/dev', '--chdir', '/home/test',
               '--clearenv', '--setenv', 'PATH', '/opt:/usr/bin',
               '--setenv', 'HOME', '/home/test', '--setenv', 'USER', 'test',
               '--setenv', 'XDG_CURRENT_DESKTOP', 'KDE', '--setenv', 'DESKTOP_SESSION', 'plasma',
               '--setenv', 'FAIL_SETUP', str(int(fail)),
               '--setenv', 'FAIL_DEFAULT', str(int(fail_default)),
               '--setenv', 'FAIL_WATCH', str(int(fail_watch)),
               '--setenv', 'FAIL_SDDM_VALIDATION', str(int(fail_sddm_validation)),
               '--setenv', 'FAIL_STOP', fail_stop,
               '--setenv', 'FAIL_RESTORE', fail_restore,
               '--setenv', 'STANDALONE', str(int(standalone)),
               '/usr/bin/bash', entry]
    command += arguments if arguments is not None else ['--preflight' if preflight else '--yes']
    return subprocess.run(command, text=True, capture_output=True, timeout=30)


def check(condition, message, result):
    if not condition:
        raise AssertionError(message + '\n' + result.stdout + result.stderr)


def test(existed, failed_setup, fail_stop="", fail_restore="", standalone=False):
    with tempfile.TemporaryDirectory(prefix='frankenstein-rollback-') as directory:
        root = Path(directory)
        fixture(root, existed, standalone)
        appearance_roots = (
            root / 'home/test/.config/kdeglobals',
            root / 'home/test/.config/plasmarc',
            root / 'home/test/.config/plasma-org.kde.plasma.desktop-appletsrc',
            root / 'home/test/.local/share/plasma',
            root / 'home/test/.local/share/color-schemes',
            root / 'home/test/.local/share/icons',
        )
        preserved = {
            path: path.read_bytes()
            for appearance_root in appearance_roots
            for path in (
                [appearance_root]
                if appearance_root.is_file()
                else list(appearance_root.rglob('*'))
            )
            if path.is_file()
        }
        state = root / 'var/lib/sddm/state.conf'
        before = (state.read_bytes(), state.stat().st_mode, state.stat().st_mtime_ns,
                  state.stat().st_uid, state.stat().st_gid) if existed else None
        result = run(root, 'install.sh', fail=failed_setup, fail_stop=fail_stop,
                     fail_restore=fail_restore if failed_setup else '',
                     arguments=['--yes', '--login', 'chooser', '--default', 'auto'])
        if failed_setup:
            check(result.returncode == 42, 'setup did not fail at the injected point', result)
        else:
            check(result.returncode == 0, 'setup failed', result)
            check('changed.desktop' in state.read_text(), 'setup did not mutate SDDM state', result)
            check('Initial default:       plasma.desktop' in result.stdout,
                  'active KDE default was not preserved', result)
            record_id = (root / 'var/lib/frankenstein/current').read_text().strip()
            record = root / f'var/lib/frankenstein/installations/{record_id}.env'
            check('SHELL_MODE=filtered' in record.read_text(),
                  'clean install did not select the KDE-compatible shell', result)
            check((root / 'home/test/.config/systemd/user/'
                   'frankenstein-omarchy-shell.service').is_file(),
                  'KDE shell user service was not installed', result)
            check((root / 'home/test/.config/autostart/'
                   'frankenstein-omarchy-shell.desktop').is_file(),
                  'KDE shell autostart was not installed', result)
            calls = (root / 'var/service-calls').read_text().splitlines()
            check('--user start frankenstein-omarchy-shell.service' in calls,
                  'KDE shell did not start in the active Plasma fixture', result)
            check(('  /home/source/uninstall.sh' if standalone else '  frankenstein uninstall')
                  in result.stdout, 'invalid rollback command', result)
            if standalone:
                bar = root / 'usr/share/frankenstein/omarchy-shell/plugins/bar'
                check(bar.is_dir() and not bar.is_symlink() and
                      not (bar / 'Bar.qml').is_symlink() and
                      'Quickshell.Hyprland' not in (bar / 'Bar.qml').read_text(),
                      'standalone payload missing KDE-compatible QML bar', result)
            result = run(root, 'uninstall.sh', fail_stop=fail_stop, fail_restore=fail_restore)
            check(result.returncode == (1 if fail_stop or fail_restore else 0), 'unexpected uninstall status', result)
        for path, content in preserved.items():
            check(path.read_bytes() == content, 'KDE user configuration modified', result)
        archives = list((root / 'home/test/.local/state/frankenstein/backups').glob('*/user-config.tar'))
        check(len(archives) == 1, 'user configuration backup missing', result)
        with tarfile.open(archives[0]) as archive:
            for path, content in preserved.items():
                member = str(path.relative_to(root / 'home/test'))
                check(archive.extractfile(member).read() == content, 'KDE backup mismatch', result)
        check('RESTORE WHILE' not in result.stderr, 'restoration raced synchronization', result)
        if fail_restore:
            check('INJECTED SDDM RESTORE FAILURE' in result.stderr, 'failure not injected', result)
            check('could not restore SDDM state' in result.stderr,
                  'missing restoration-failure diagnostic', result)
            check('completed mutations were rolled back' not in result.stderr,
                  'false rollback success', result)
            check('integration removed' not in result.stdout, 'false uninstall success', result)
            check('changed.desktop' in state.read_text(), 'mutated state unexpectedly lost', result)
            check((root / 'var/lib/omarchy-desktop-manager/default-session').exists(),
                  'default preference lost', result)
            check((root / 'etc/sddm.conf.d/zzzz-frankenstein.conf').exists(), 'override lost', result)
            backups = list((root / 'var/lib/frankenstein/backups').glob('*/sddm-state.existed'))
            check(len(backups) == 1, 'recovery metadata lost', result)
            if existed:
                backup = backups[0].with_name('sddm-state.conf')
                check(backup.read_bytes() == before[0], 'original backup corrupted', result)
            check(not list(state.parent.glob('.state.conf.frankenstein.*')),
                  'temporary restoration file leaked', result)
            if not failed_setup:
                check((root / 'var/lib/frankenstein/current').exists(), 'retry record lost', result)
                retry = run(root, 'uninstall.sh')
                check(retry.returncode == 0, 'uninstall retry failed', retry)
                if existed:
                    check(state.read_bytes() == before[0], 'retry did not restore original', retry)
                else:
                    check(not state.exists(), 'retry did not remove originally absent state', retry)
            print(f'PASS: {"failed setup" if failed_setup else "uninstall"}, '
                  f'{fail_restore} restoration failure preserves recovery data')
            return
        if fail_stop:
            check('could not stop SDDM synchronization' in result.stderr,
                  'missing stop-failure diagnostic', result)
            check('changed.desktop' in state.read_text(), 'unsafe restoration after stop failure', result)
            check((root / 'var/lib/omarchy-desktop-manager/default-session').exists(),
                  'preference removed after stop failure', result)
            if not failed_setup:
                check((root / 'var/lib/frankenstein/current').exists(), 'retry record lost', result)
            check(bool(list((root / 'var/lib/frankenstein/backups').glob('*/sddm-state.existed'))),
                  'recovery backup lost after stop failure', result)
            print(f'PASS: {"failed setup" if failed_setup else "uninstall"}, '
                  f'{fail_stop} stop failure preserves recovery data')
            return
        if existed:
            after = (state.read_bytes(), state.stat().st_mode, state.stat().st_mtime_ns,
                     state.stat().st_uid, state.stat().st_gid)
            check(before == after, 'original state bytes/metadata not restored', result)
        else:
            check(not state.exists(), 'initially absent SDDM state not removed', result)
        if standalone:
            check(not (root / 'usr/share/frankenstein/omarchy-shell').exists(), 'standalone shell remains', result)
            check(not (root / 'usr/lib/frankenstein/installer-state').exists(), 'standalone helper remains', result)
        else:
            check((root / 'usr/lib/frankenstein/installer-state').exists(), 'package-owned helper removed', result)
        check(not (root / 'var/lib/frankenstein/current').exists(), 'active record remains', result)
        check(not (root / 'var/lib/omarchy-desktop-manager').exists(), 'default preference remains', result)
        check(not (root / 'etc/sddm.conf.d/zzzz-frankenstein.conf').exists(), 'override remains', result)
        check((root / 'etc/sddm.conf.d/original.conf').read_text() == '[Theme]\nCurrent=omarchy\n',
              'original SDDM config changed', result)
        check(bool(list((root / 'var/lib/frankenstein/backups').glob('*/sddm-state.existed'))),
              'recovery backup lost', result)
        calls = (root / 'var/service-calls').read_text().splitlines()
        check(calls.index('disable --now omarchy-desktop-manager-default.path') <
              calls.index('stop omarchy-desktop-manager-default.service'), 'wrong stop order', result)
        print(f'PASS: {"failed setup" if failed_setup else "uninstall"}, '
              f'{"existing" if existed else "absent"} SDDM state')


def test_conflict(standalone, path, dangling):
    with tempfile.TemporaryDirectory(prefix='frankenstein-conflict-') as directory:
        root = Path(directory)
        fixture(root, True, standalone)
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if dangling:
            target.symlink_to('/nonexistent-frankenstein-fixture')
        else:
            target.write_text('existing user-owned content\n')
        result = run(root, 'install.sh')
        check(result.returncode == 1 and 'already exists' in result.stderr,
              'existing path not refused during preflight: ' + path, result)
        check(not (root / 'var/lib/frankenstein/backups').exists(),
              'conflict detected only after mutation', result)
        if dangling:
            check(target.is_symlink() and os.readlink(target) == '/nonexistent-frankenstein-fixture',
                  'existing symlink changed', result)
        else:
            check(target.read_text() == 'existing user-owned content\n', 'existing file changed', result)
        print(f'PASS: conflict refused ({"symlink" if dangling else "file"}): {path}')


def test_sddm_precedence(standalone, scenario):
    with tempfile.TemporaryDirectory(prefix='frankenstein-preflight-') as directory:
        root = Path(directory)
        fixture(root, True, standalone)
        vendor = 'usr/lib/sddm/sddm.conf.d'
        # The fixture must not follow a host-library symlink when seeding data.
        link = root / 'usr/lib/sddm'
        if link.is_symlink():
            link.unlink()
        put(root, vendor + '/00-vendor.conf', '[Theme]\nCurrent=vendor\n')
        if scenario == 'local':
            put(root, 'etc/sddm.conf.d/original.conf', '[Theme]\nCurrent=breeze\n')
        elif scenario == 'main':
            put(root, 'etc/sddm.conf.d/original.conf', '[Theme]\nCurrent=local\n')
            put(root, 'etc/sddm.conf', '[Theme]\n  Current = breeze  \n')
        elif scenario == 'main-conflict':
            put(root, 'etc/sddm.conf', '[Autologin]\n User = existing-user \n')
        elif scenario == 'late-conflict':
            put(root, 'etc/sddm.conf.d/zzzzz-local.conf', '[Autologin]\nUser=existing-user\n')
        else:
            raise AssertionError(scenario)
        result = run(root, 'install.sh', arguments=['--preflight', '--login', 'chooser'])
        if scenario.endswith('conflict'):
            check(result.returncode == 1 and 'overrides the proposed' in result.stderr,
                  'ineffective SDDM override accepted', result)
        else:
            check(result.returncode == 0 and 'SDDM action:           preserve' in result.stdout,
                  'SDDM precedence misread', result)
        check(not (root / 'var/lib/frankenstein').exists(), 'preflight mutated system state', result)
        check(not (root / 'var/service-calls').exists(), 'preflight changed services', result)
        print('PASS: SDDM preflight precedence:', scenario)


def appearance_snapshot(root):
    appearance_roots = (
        root / 'home/test/.config/kdeglobals',
        root / 'home/test/.config/plasmarc',
        root / 'home/test/.config/plasma-org.kde.plasma.desktop-appletsrc',
        root / 'home/test/.local/share/plasma',
        root / 'home/test/.local/share/color-schemes',
        root / 'home/test/.local/share/icons',
    )
    return {
        path: path.read_bytes()
        for appearance_root in appearance_roots
        for path in (
            [appearance_root]
            if appearance_root.is_file()
            else list(appearance_root.rglob('*'))
        )
        if path.is_file()
    }


def test_sddm_validation_failure(standalone):
    with tempfile.TemporaryDirectory(prefix='frankenstein-sddm-invalid-') as directory:
        root = Path(directory)
        fixture(root, True, standalone)
        before = appearance_snapshot(root)
        result = run(
            root,
            'install.sh',
            fail_sddm_validation=True,
            arguments=['--yes', '--login', 'frankenstein', '--default', 'keep'],
        )
        check(result.returncode == 46, 'invalid SDDM theme did not fail closed', result)
        check('INJECTED SDDM VALIDATION FAILURE' in result.stderr,
              'missing SDDM validation diagnostic', result)
        check(not (root / 'var/lib/frankenstein').exists(),
              'validation failed only after installer mutation', result)
        check(not (root / 'etc/sddm.conf.d/zzzz-frankenstein.conf').exists(),
              'invalid SDDM theme became active', result)
        check(before == appearance_snapshot(root), 'appearance changed on validation failure', result)
        print('PASS: invalid SDDM theme fails before mutation')


def test_frankenstein_theme_round_trip(standalone):
    with tempfile.TemporaryDirectory(prefix='frankenstein-sddm-round-trip-') as directory:
        root = Path(directory)
        fixture(root, True, standalone)
        before = appearance_snapshot(root)
        install_result = run(
            root,
            'install.sh',
            arguments=['--yes', '--login', 'frankenstein', '--default', 'keep'],
        )
        check(install_result.returncode == 0, 'Frankenstein theme setup failed', install_result)
        override = root / 'etc/sddm.conf.d/zzzz-frankenstein.conf'
        check('Current=frankenstein' in override.read_text(),
              'Frankenstein theme was not selected', install_result)
        uninstall_result = run(root, 'uninstall.sh')
        check(uninstall_result.returncode == 0, 'Frankenstein theme rollback failed',
              uninstall_result)
        check(not override.exists(), 'Frankenstein SDDM override remains after rollback',
              uninstall_result)
        check((root / 'etc/sddm.conf.d/original.conf').read_text()
              == '[Theme]\nCurrent=omarchy\n',
              'previous SDDM theme was disturbed', uninstall_result)
        check(before == appearance_snapshot(root), 'appearance changed during SDDM round trip',
              uninstall_result)
        print('PASS: Frankenstein SDDM round trip preserves Plasma appearance')


def test_fresh_shell_soft_default(user_disables):
    with tempfile.TemporaryDirectory(prefix='frankenstein-fresh-shell-') as directory:
        root = Path(directory)
        fixture(root, True, False)
        applets = root / 'home/test/.config/plasma-org.kde.plasma.desktop-appletsrc'
        applets.unlink()
        result = run(root, 'install.sh')
        check(result.returncode == 0, 'fresh-profile setup failed', result)
        profile = root / 'home/test/.config/frankenstein/plasma.json'
        check(profile.is_file() and
              json.loads(profile.read_text())['shell']['panel'] == 'omarchy',
              'fresh profile did not receive the Omarchy top-bar soft default', result)
        record_id = (root / 'var/lib/frankenstein/current').read_text().strip()
        record = root / f'var/lib/frankenstein/installations/{record_id}.env'
        check('SHELL_PROFILE_DEFAULT_CREATED=true' in record.read_text(),
              'top-bar soft-default ownership was not recorded', result)
        check(not applets.exists(),
              'fresh shell default created or replaced a Plasma panel layout', result)

        if user_disables:
            profile.write_text(
                '{\n  "schemaVersion": 1,\n  "shell": {\n    "panel": "native"\n  }\n}\n'
            )
        uninstall = run(root, 'uninstall.sh')
        check(uninstall.returncode == 0, 'fresh-profile uninstall failed', uninstall)
        check(profile.exists() == user_disables,
              'uninstall did not respect the user shell-profile choice', uninstall)
        if user_disables:
            check(json.loads(profile.read_text())['shell']['panel'] == 'native',
                  'uninstall changed the disabled bar choice', uninstall)
        print(f'PASS: fresh Omarchy bar soft default, user_disables={user_disables}')


def test_bar_control():
    with tempfile.TemporaryDirectory(prefix='frankenstein-bar-control-') as directory:
        root = Path(directory)
        fixture(root, True, False)
        profile = root / 'home/test/.config/frankenstein/plasma.json'
        applets = root / 'home/test/.config/plasma-org.kde.plasma.desktop-appletsrc'
        applets_before = applets.read_bytes()

        enabled = run(root, 'adapter', arguments=['bar', 'enable'])
        check(enabled.returncode == 0, 'bar enable failed', enabled)
        check(json.loads(profile.read_text())['shell']['panel'] == 'omarchy',
              'bar enable did not select the Omarchy panel', enabled)
        check(applets.read_bytes() == applets_before,
              'bar enable changed the Plasma panel layout', enabled)

        disabled = run(root, 'adapter', arguments=['bar', 'disable'])
        check(disabled.returncode == 0, 'bar disable failed', disabled)
        check(json.loads(profile.read_text())['shell']['panel'] == 'native',
              'bar disable did not select the native panel', disabled)
        check(applets.read_bytes() == applets_before,
              'bar disable changed the Plasma panel layout', disabled)

        before_failure = profile.read_bytes()
        failed = run(root, 'adapter', fail=True, arguments=['bar', 'enable'])
        check(failed.returncode != 0, 'failed bar restart was accepted', failed)
        check(profile.read_bytes() == before_failure,
              'failed bar restart did not restore the prior profile', failed)
        check(applets.read_bytes() == applets_before,
              'failed bar restart changed the Plasma panel layout', failed)

        status = run(root, 'adapter', arguments=['bar', 'status'])
        check(status.returncode == 0 and status.stdout.strip() == 'native',
              'bar status did not report the restored native mode', status)
        print('PASS: bar enable, disable, status, and rollback')


if __name__ == '__main__':
    if not shutil.which('bwrap'):
        raise SystemExit('bwrap is required; refusing to run unsandboxed')
    for standalone in (False, True):
        print('Layout:', 'standalone' if standalone else 'packaged')
        for failed in (True, False):
            for existing in (True, False):
                test(existing, failed, standalone=standalone)
            for stop_unit in ('path', 'service'):
                test(True, failed, stop_unit, standalone=standalone)
            for failure in ('directory', 'temporary', 'copy', 'rename', 'remove'):
                test(failure != 'remove', failed, fail_restore=failure, standalone=standalone)
        conflicts = ['etc/sddm.conf.d/zzzz-frankenstein.conf',
                     'home/test/.config/autostart/frankenstein-omarchy-shell.desktop']
        if standalone:
            conflicts += ['usr/lib/frankenstein/installer-state', 'usr/lib/frankenstein/shell-profile']
        for path in conflicts:
            for dangling in (False, True):
                test_conflict(standalone, path, dangling)
        for scenario in ('local', 'main', 'main-conflict', 'late-conflict'):
            test_sddm_precedence(standalone, scenario)
        test_sddm_validation_failure(standalone)
        test_frankenstein_theme_round_trip(standalone)
    test_fresh_shell_soft_default(False)
    test_fresh_shell_soft_default(True)
    test_bar_control()
