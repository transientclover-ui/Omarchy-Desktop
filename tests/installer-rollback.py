#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT
"""Run real packaged setup/uninstall in bubblewrap with simulated system services.

Requires Linux user namespaces, bwrap, Python 3, bash, and jq. Never falls back
outside the sandbox. The host filesystem is read-only; only temporary fixtures
are writable. No root privileges, package transactions, or real services run.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

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


def fixture(root, existed):
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
    }.items():
        put(root, 'usr/share/omarchy/shell/' + name, content + '\n')
    for source, destination in {
        'install.sh': 'usr/lib/frankenstein/install.sh',
        'uninstall.sh': 'usr/lib/frankenstein/uninstall.sh',
        'src/lib/installer-state.sh': 'usr/lib/frankenstein/installer-state',
        'src/lib/shell-profile.sh': 'usr/lib/frankenstein/shell-profile',
        'src/bin/frankenstein-shell-adapter': 'usr/bin/frankenstein-shell-adapter',
        'src/bin/omarchy-default-desktop': 'usr/bin/omarchy-default-desktop',
        'src/frankenstein/plasma-shell-profile.json': 'usr/share/frankenstein/profiles/plasma.json',
        'src/frankenstein/plasma-menu.jsonc': 'usr/share/frankenstein/profiles/plasma-menu.jsonc',
        'src/frankenstein/zzzz-frankenstein.conf': 'usr/share/frankenstein/templates/zzzz-omarchy-desktop-manager.conf',
        'src/frankenstein/frankenstein-omarchy-shell-autostart.desktop': 'usr/share/frankenstein/templates/frankenstein-omarchy-shell.desktop',
        'src/frankenstein/frankenstein-omarchy-menu.desktop': 'usr/share/frankenstein/templates/frankenstein-omarchy-menu.desktop',
        'src/systemd/frankenstein-omarchy-shell.service': 'usr/share/frankenstein/templates/frankenstein-omarchy-shell.service',
    }.items():
        copy(root, source, destination)
    for unit in ('path', 'service'):
        name = 'omarchy-desktop-manager-default.' + unit
        copy(root, 'src/systemd/' + name, 'usr/lib/systemd/system/' + name)
    for name in ('shell.qml', 'services/PluginRegistry.qml', 'plugins/menu/Menu.qml'):
        copy(root, 'src/frankenstein/omarchy-shell/' + name,
             'usr/share/frankenstein/omarchy-shell/' + name)
    state = root / 'var/lib/sddm/state.conf'
    if existed:
        state.write_text('[Last]\nSession=original.desktop\nUser=original\n')
        state.chmod(0o640)
        os.utime(state, (1700000000, 1700000000))
    put(root, 'mock/pacman', '''#!/bin/bash
case "$*" in
  '-Q omarchy') echo 'omarchy 4.0.4-1';;
  '-Q frankenstein-core'|'-Q frankenstein-kde') exit 0;;
  '-Qq') printf '%s\\n' omarchy frankenstein-core frankenstein-kde;;
  *) exit 90;;
esac
''', True)
    put(root, 'mock/sudo', '''#!/bin/bash
[[ $1 == -v ]] && exit 0
# Every restore must occur after both simulated systemd units stop.
case "$1:$*" in
  mv:*state.conf*|rm:*sddm/state.conf*)
    if [[ -e /var/path-active || -e /var/sync-active ]]; then
      echo 'RESTORE WHILE SYNCHRONIZATION ACTIVE' >&2
      exit 91
    fi;;
esac
exec "$@"
''', True)
    put(root, 'mock/systemctl', '''#!/bin/bash
printf '%s\\n' "$*" >>/var/service-calls
case "$*" in
  'enable --now omarchy-desktop-manager-default.path') touch /var/path-active;;
  'disable --now omarchy-desktop-manager-default.path')
    [[ ${FAIL_STOP:-} == path ]] && exit 43
    rm -f /var/path-active;;
  'stop omarchy-desktop-manager-default.service')
    [[ ${FAIL_STOP:-} == service ]] && exit 43
    rm -f /var/sync-active;;
  '--user start frankenstein-omarchy-shell.service')
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
''', True)
    for name in ('quickshell', 'qs', 'systemsettings', 'xdg-terminal-exec', 'qdbus6'):
        put(root, 'mock/' + name, '#!/bin/bash\nexit 93\n', True)


def run(root, script, fail=False, fail_stop=""):
    command = ['bwrap', '--ro-bind', '/', '/', '--unshare-all', '--die-with-parent',
               '--ro-bind', '/usr', '/mnt', '--bind', str(root / 'usr'), '/usr',
               '--bind', str(root / 'etc'), '/etc', '--bind', str(root / 'var'), '/var',
               '--bind', str(root / 'home'), '/home', '--ro-bind', str(root / 'mock'), '/opt',
               '--tmpfs', '/tmp', '--proc', '/proc', '--dev', '/dev', '--chdir', '/home/test',
               '--clearenv', '--setenv', 'PATH', '/opt:/usr/bin',
               '--setenv', 'HOME', '/home/test', '--setenv', 'USER', 'test',
               '--setenv', 'XDG_CURRENT_DESKTOP', 'KDE', '--setenv', 'DESKTOP_SESSION', 'plasma',
               '--setenv', 'FAIL_SETUP', str(int(fail)),
               '--setenv', 'FAIL_STOP', fail_stop,
               '/usr/bin/bash', '/usr/lib/frankenstein/' + script, '--yes']
    return subprocess.run(command, text=True, capture_output=True, timeout=30)


def check(condition, message, result):
    if not condition:
        raise AssertionError(message + '\n' + result.stdout + result.stderr)


def test(existed, failed_setup, fail_stop=""):
    with tempfile.TemporaryDirectory(prefix='frankenstein-rollback-') as directory:
        root = Path(directory)
        fixture(root, existed)
        state = root / 'var/lib/sddm/state.conf'
        before = (state.read_bytes(), state.stat().st_mode, state.stat().st_mtime_ns,
                  state.stat().st_uid, state.stat().st_gid) if existed else None
        result = run(root, 'install.sh', fail=failed_setup, fail_stop=fail_stop)
        if failed_setup:
            check(result.returncode == 42, 'setup did not fail at the injected point', result)
        else:
            check(result.returncode == 0, 'setup failed', result)
            check('changed.desktop' in state.read_text(), 'setup did not mutate SDDM state', result)
            result = run(root, 'uninstall.sh', fail_stop=fail_stop)
            check(result.returncode == (1 if fail_stop else 0), 'unexpected uninstall status', result)
        check('RESTORE WHILE' not in result.stderr, 'restoration raced synchronization', result)
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


if __name__ == '__main__':
    if not shutil.which('bwrap'):
        raise SystemExit('bwrap is required; refusing to run unsandboxed')
    for failed in (True, False):
        for existing in (True, False):
            test(existing, failed)
        for stop_unit in ('path', 'service'):
            test(True, failed, stop_unit)
