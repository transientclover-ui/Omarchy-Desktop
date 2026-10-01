#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT
"""Test preservation of an existing KDE/Omarchy setup in isolated fixtures."""
import importlib.util
from pathlib import Path
import tempfile

spec = importlib.util.spec_from_file_location('rollback', Path(__file__).with_name('installer-rollback.py'))
rollback = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rollback)


def snapshot(root):
    entries = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            entries[str(path.relative_to(root))] = ('link', str(path.readlink()))
        elif path.is_file():
            stat = path.stat()
            entries[str(path.relative_to(root))] = ('file', path.read_bytes(), stat.st_mode, stat.st_mtime_ns)
    return entries


def test(standalone, enabled=True, failed_setup=False, failed_restore=False):
    with tempfile.TemporaryDirectory(prefix='frankenstein-preserve-') as directory:
        root = Path(directory)
        rollback.fixture(root, True, standalone)
        unit = rollback.put(root, 'home/test/.config/systemd/user/omarchy-shell.service',
                            '[Service]\nExecStart=/usr/bin/quickshell -n -p /usr/share/omarchy/shell\n')
        if enabled:
            wanted = root / 'home/test/.config/systemd/user/graphical-session.target.wants'
            wanted.mkdir()
            (wanted / unit.name).symlink_to('../omarchy-shell.service')
            rollback.put(root, 'var/original-shell-active', 'running\n')
        for path, content in {
            'shell.json': '{"disabledPlugins":["omarchy.lock"],"plugins":[{"id":"example.plugin"}],'
                          '"bar":{"layout":{"right":[{"id":"custom-command","type":"command","exec":"user-command"}]}}}\n',
            'plugins/example.plugin/Plugin.qml': '// User-owned plugin\n',
            'extensions/omarchy-menu.jsonc': '// User menu extension\n',
            'bar/scripts/user-command': '#!/bin/sh\nprintf custom\n',
        }.items():
            rollback.put(root, 'home/test/.config/omarchy/' + path, content)
        rollback.put(root, 'home/test/.config/frankenstein/shell-disabled', 'existing preference\n')
        rollback.put(root, 'home/test/.config/autostart/user-app.desktop', '[Desktop Entry]\nName=Keep me\n')
        rollback.put(root, 'mock/qs', '''#!/bin/bash
printf '%s\\n' "$*" >>/var/ipc-calls
case "$*" in
  'list --json -p /usr/share/omarchy/shell') echo '[{"pid":123}]';;
  'ipc -n -p /usr/share/omarchy/shell call -- shell ping') echo ok;;
  'ipc -n -p /usr/share/omarchy/shell call -- shell summon omarchy.menu '*) echo ok;;
  *) exit 93;;
esac
''', True)
        config = root / 'home/test/.config'
        before = snapshot(config)
        state = root / 'var/lib/sddm/state.conf'
        original_state = state.read_bytes()
        sddm_before = snapshot(root / 'etc')
        preflight = rollback.run(
            root, 'install.sh', arguments=['--preflight', '--shell', 'preserve'])
        rollback.check(preflight.returncode == 0 and 'Shell integration:     preserve' in preflight.stdout,
                       'preservation not selected', preflight)
        result = rollback.run(
            root, 'install.sh', fail_watch=failed_setup,
            fail_restore='rename' if failed_setup and failed_restore else '',
            arguments=['--yes', '--shell', 'preserve'])
        rollback.check(result.returncode == (42 if failed_setup else 0), 'unexpected setup result', result)
        rollback.check(snapshot(config) == before, 'setup changed existing settings', result)
        rollback.check(not (root / 'home/test/.local/share/applications/frankenstein-omarchy-menu.desktop').exists(),
                       'replacement menu was installed', result)
        rollback.check(snapshot(root / 'etc') == sddm_before, 'existing SDDM settings changed', result)
        rollback.check(state.read_bytes() == original_state, 'setup changed remembered session', result)
        rollback.check(not (root / 'var/lib/omarchy-desktop-manager/default-session').exists(),
                       'setup forced a new default', result)
        if not failed_setup:
            record_id = (root / 'var/lib/frankenstein/current').read_text().strip()
            record = root / f'var/lib/frankenstein/installations/{record_id}.env'
            rollback.check('SHELL_MODE=preserve' in record.read_text(), 'mode not recorded', result)
            for command in ('run', 'enable', 'disable'):
                blocked = rollback.run(root, 'adapter', arguments=[command])
                rollback.check(blocked.returncode == 1 and 'existing Omarchy shell is preserved' in blocked.stderr,
                               'adapter could replace preserved shell', blocked)
            checked = rollback.run(root, 'adapter', arguments=['check'])
            rollback.check(checked.returncode == (0 if enabled else 1) and
                           'plugin_compatibility=not-certified' in checked.stdout,
                           'preservation check misreported status', checked)
            if enabled:
                menu = rollback.run(root, 'adapter', arguments=['menu'])
                rollback.check(menu.returncode == 0, 'menu did not route to existing shell', menu)
            result = rollback.run(root, 'uninstall.sh', fail_restore='rename' if failed_restore else '')
            rollback.check(result.returncode == (1 if failed_restore else 0), 'unexpected uninstall result', result)
            if failed_restore:
                rollback.check(snapshot(config) == before, 'failed uninstall changed settings', result)
                result = rollback.run(root, 'uninstall.sh')
                rollback.check(result.returncode == 0, 'retry failed', result)
        if not (failed_setup and failed_restore):
            rollback.check(state.read_bytes() == original_state, 'SDDM state not restored', result)
        rollback.check(snapshot(config) == before, 'rollback/uninstall changed existing settings', result)
        calls = (root / 'var/service-calls').read_text().splitlines()
        rollback.check(not any(call.startswith('--user ') for call in calls),
                       'existing-shell mode mutated user services: ' + repr(calls), result)
        rollback.check((root / 'var/original-shell-active').exists() == enabled,
                       'original runtime changed', result)
        print(f'PASS: preserve {"standalone" if standalone else "packaged"}, enabled={enabled}, '
              f'failed_setup={failed_setup}, failed_restore={failed_restore}')


def test_category(standalone, category):
    with tempfile.TemporaryDirectory(prefix='frankenstein-category-') as directory:
        root = Path(directory)
        rollback.fixture(root, True, standalone)
        rollback.put(root, 'home/test/.config/systemd/user/omarchy-shell.service', '[Service]\nExecStart=quickshell\n')
        wanted = root / 'home/test/.config/systemd/user/graphical-session.target.wants'
        wanted.mkdir()
        (wanted / 'omarchy-shell.service').symlink_to('../omarchy-shell.service')
        rollback.put(root, 'var/original-shell-active', 'running\n')
        before = snapshot(root / 'home/test/.config')
        original_state = (root / 'var/lib/sddm/state.conf').read_bytes()
        flags = {'login': ['--login', 'chooser'], 'default': ['--default', 'plasma'],
                 'shell': ['--shell', 'filtered']}[category]
        arguments = ['--yes', *flags]
        if category != 'shell':
            arguments += ['--shell', 'preserve']
        result = rollback.run(root, 'install.sh', arguments=arguments)
        rollback.check(result.returncode == 0, 'selective setup failed', result)
        override = root / 'etc/sddm.conf.d/zzzz-frankenstein.conf'
        rollback.check(override.exists() == (category == 'login'), 'login settings changed without selection', result)
        rollback.check(((root / 'var/lib/sddm/state.conf').read_bytes() != original_state) == (category == 'default'),
                       'default changed without selection', result)
        rollback.check((root / 'var/original-shell-active').exists() == (category != 'shell'),
                       'shell changed without selection', result)
        if category != 'shell':
            rollback.check(snapshot(root / 'home/test/.config') == before, 'unselected user settings changed', result)
        result = rollback.run(root, 'uninstall.sh')
        rollback.check(result.returncode == 0, 'selective uninstall failed', result)
        rollback.check(snapshot(root / 'home/test/.config') == before, 'original settings not restored', result)
        rollback.check((root / 'var/original-shell-active').exists(), 'original shell not restored', result)
        print(f'PASS: selective {category}, {"standalone" if standalone else "packaged"}')


def test_auto_adopts_existing(standalone):
    with tempfile.TemporaryDirectory(prefix='frankenstein-auto-shell-') as directory:
        root = Path(directory)
        rollback.fixture(root, True, standalone)
        unit = rollback.put(
            root, 'home/test/.config/systemd/user/omarchy-shell.service',
            '[Service]\nExecStart=/usr/bin/quickshell -n -p /usr/share/omarchy/shell\n')
        wanted = root / 'home/test/.config/systemd/user/graphical-session.target.wants'
        wanted.mkdir()
        (wanted / unit.name).symlink_to('../omarchy-shell.service')
        rollback.put(root, 'var/original-shell-active', 'running\n')
        rollback.put(root, 'home/test/.config/omarchy/shell.json',
                     '{"version":1,"bar":{"layout":{"left":[],"center":[],"right":[]}}}\n')
        shell_before = snapshot(root / 'home/test/.config/omarchy')
        sddm_before = snapshot(root / 'etc')
        state_before = (root / 'var/lib/sddm/state.conf').read_bytes()

        result = rollback.run(root, 'install.sh')
        rollback.check(result.returncode == 0 and
                       'Shell integration:     filtered' in result.stdout,
                       'auto did not adopt the existing stock shell', result)
        record_id = (root / 'var/lib/frankenstein/current').read_text().strip()
        record = root / f'var/lib/frankenstein/installations/{record_id}.env'
        rollback.check('SHELL_MODE=filtered' in record.read_text(),
                       'adapter mode was not recorded', result)
        rollback.check(not (root / 'var/original-shell-active').exists(),
                       'stock shell remained active', result)
        rollback.check((root / 'home/test/.config/systemd/user/'
                        'frankenstein-omarchy-shell.service').is_file(),
                       'adapter service missing', result)
        rollback.check((root / 'home/test/.config/autostart/'
                        'frankenstein-omarchy-shell.desktop').is_file(),
                       'adapter autostart missing', result)
        rollback.check(snapshot(root / 'home/test/.config/omarchy') == shell_before,
                       'Omarchy user configuration changed', result)
        rollback.check(snapshot(root / 'etc') == sddm_before,
                       'SDDM configuration changed', result)
        rollback.check((root / 'var/lib/sddm/state.conf').read_bytes() == state_before,
                       'remembered SDDM session changed', result)

        result = rollback.run(root, 'uninstall.sh')
        rollback.check(result.returncode == 0, 'adapter uninstall failed', result)
        rollback.check((root / 'var/original-shell-active').exists(),
                       'original shell runtime was not restored', result)
        rollback.check((wanted / unit.name).is_symlink(),
                       'original shell enablement was not restored', result)
        rollback.check(not (root / 'home/test/.config/systemd/user/'
                            'frankenstein-omarchy-shell.service').exists(),
                       'adapter service remained after uninstall', result)
        rollback.check(snapshot(root / 'home/test/.config/omarchy') == shell_before,
                       'rollback changed Omarchy user configuration', result)
        print(f'PASS: auto KDE shell adoption, {"standalone" if standalone else "packaged"}')


def test_preserve_migration(fail_health=False):
    with tempfile.TemporaryDirectory(prefix='frankenstein-shell-migration-') as directory:
        root = Path(directory)
        rollback.fixture(root, True, False)
        unit = rollback.put(
            root, 'home/test/.config/systemd/user/omarchy-shell.service',
            '[Service]\nExecStart=/usr/bin/quickshell -n -p /usr/share/omarchy/shell\n')
        wanted = root / 'home/test/.config/systemd/user/graphical-session.target.wants'
        wanted.mkdir()
        (wanted / unit.name).symlink_to('../omarchy-shell.service')
        rollback.put(root, 'var/original-shell-active', 'running\n')
        sddm_config_before = snapshot(root / 'etc')
        sddm_state_before = (root / 'var/lib/sddm/state.conf').read_bytes()

        setup = rollback.run(
            root, 'install.sh', arguments=['--yes', '--shell', 'preserve'])
        rollback.check(setup.returncode == 0, 'preserve setup failed', setup)
        record_id = (root / 'var/lib/frankenstein/current').read_text().strip()
        record = root / f'var/lib/frankenstein/installations/{record_id}.env'
        rollback.put(root, 'usr/bin/frankenstein-shell-adapter',
                     '#!/bin/bash\n[[ $1 == check ]] || exit 2\n'
                     f'exit {1 if fail_health else 0}\n', True)
        if fail_health:
            rollback.put(root, 'mock/sleep', '#!/bin/bash\nexit 0\n', True)

        migration = rollback.run(root, 'migration', arguments=[])
        expected_status = 1 if fail_health else 0
        rollback.check(migration.returncode == expected_status,
                       'unexpected migration result', migration)
        rollback.check(snapshot(root / 'etc') == sddm_config_before,
                       'migration changed SDDM configuration', migration)
        rollback.check((root / 'var/lib/sddm/state.conf').read_bytes() == sddm_state_before,
                       'migration changed SDDM state', migration)

        service = root / 'home/test/.config/systemd/user/frankenstein-omarchy-shell.service'
        autostart = root / 'home/test/.config/autostart/frankenstein-omarchy-shell.desktop'
        menu = root / 'home/test/.local/share/applications/frankenstein-omarchy-menu.desktop'
        if fail_health:
            rollback.check('SHELL_MODE=preserve' in record.read_text(),
                           'failed migration did not restore shell mode', migration)
            rollback.check(not service.exists() and not autostart.exists() and not menu.exists(),
                           'failed migration left integration files', migration)
            rollback.check((root / 'var/original-shell-active').exists() and
                           (wanted / unit.name).is_symlink(),
                           'failed migration did not restore stock shell', migration)
        else:
            record_text = record.read_text()
            rollback.check('SHELL_MODE=filtered' in record_text and
                           'EXISTING_SHELL_ENABLED=true' in record_text and
                           'EXISTING_SHELL_ACTIVE=true' in record_text,
                           'migration state is incomplete', migration)
            rollback.check(service.is_file() and autostart.is_file() and menu.is_file(),
                           'migration integration files are incomplete', migration)
            rollback.check(not (root / 'var/original-shell-active').exists() and
                           not (wanted / unit.name).exists(),
                           'migration left the stock shell active', migration)
            uninstall = rollback.run(root, 'uninstall.sh')
            rollback.check(uninstall.returncode == 0, 'migrated uninstall failed', uninstall)
            rollback.check((root / 'var/original-shell-active').exists() and
                           (wanted / unit.name).is_symlink(),
                           'migrated uninstall did not restore stock shell', uninstall)
        print(f'PASS: preserve-to-adapter migration, fail_health={fail_health}')


if __name__ == '__main__':
    for standalone in (False, True):
        test(standalone)
        test(standalone, enabled=False)
        test(standalone, failed_restore=True)
        test(standalone, failed_setup=True)
        test(standalone, failed_setup=True, failed_restore=True)
        for category in ('login', 'default', 'shell'):
            test_category(standalone, category)
        test_auto_adopts_existing(standalone)
    test_preserve_migration()
    test_preserve_migration(fail_health=True)
