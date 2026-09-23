#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT
"""Selection tests use temporary config and mocked read-only IPC/UI only."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'src/bin/frankenstein-settings'


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='frankenstein-settings-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / '.config/omarchy/shell.json'
        self.config.parent.mkdir(parents=True)
        self.custom = {'id': 'custom-status', 'type': 'command', 'exec': 'touch NEVER_EXECUTE',
                       'onClick': 'user-click-command', 'interval': 5, 'tooltip': 'Keep all details',
                       'extra': {'future-field': True}}
        self.original = {'version': 1, 'disabledPlugins': ['already.disabled'],
                         'plugins': [{'id': 'example.panel', 'userSetting': 42}],
                         'idle': {'lock': 300}, 'unrelated': {'keep': True},
                         'bar': {'position': 'top', 'layout': {
                             'left': [{'id': 'omarchy.menu'}],
                             'center': [{'id': 'omarchy.clock', 'format': 'HH:mm'}],
                             'right': [self.custom, {'id': 'example.panel'},
                                       dict(self.custom, interval=17)]}}}
        self.config.write_text(json.dumps(self.original, indent=2) + '\n')
        self.raw = self.config.read_bytes()
        self.plugins = self.root / 'plugins.json'
        self.plugins.write_text(json.dumps([
            {'id': 'omarchy.bar', 'name': 'Bar', 'kinds': ['bar'], 'enabled': True, 'canDisable': False},
            {'id': 'example.panel', 'name': 'Example panel', 'kinds': ['panel', 'bar-widget'], 'enabled': True},
            {'id': 'omarchy.clock', 'name': 'Clock', 'kinds': ['bar-widget'], 'enabled': True},
            {'id': 'already.disabled', 'name': 'Disabled', 'kinds': ['service'], 'enabled': False},
        ]))
        mock = self.root / 'bin'
        mock.mkdir()
        self.make_executable(mock / 'qs', '#!/bin/bash\ncat "$MOCK_PLUGINS"\n')
        self.make_executable(mock / 'gum', '''#!/bin/bash
[[ ${MOCK_CANCEL:-0} == 1 ]] && exit 130
if [[ -n ${MOCK_DROP:-} ]]; then
  awk -v drop="$MOCK_DROP" 'index($0, drop) == 0'
else
  cat
fi
[[ ${MOCK_CONCURRENT:-0} != 1 ]] || printf '\\n' >>"$XDG_CONFIG_HOME/omarchy/shell.json"
exit 0
''')
        self.env = dict(os.environ, HOME=str(self.root), XDG_CONFIG_HOME=str(self.root / '.config'),
                        XDG_STATE_HOME=str(self.root / '.local/state'), MOCK_PLUGINS=str(self.plugins),
                        PATH=str(mock) + ':' + os.environ['PATH'])
        for name in ('MOCK_DROP', 'MOCK_CANCEL', 'MOCK_CONCURRENT'):
            self.env.pop(name, None)

    def make_executable(self, path, content):
        path.write_text(content)
        path.chmod(0o755)

    def run_script(self, *args, text=''):
        return subprocess.run(['bash', str(SCRIPT), *args], input=text, text=True,
                              capture_output=True, env=self.env, cwd=self.root, timeout=10)

    def test_catalog_includes_custom_instances_and_omits_disabled(self):
        result = self.run_script('--list')
        self.assertEqual(result.returncode, 0, result.stderr)
        catalog = json.loads(result.stdout)
        self.assertEqual([x['key'] for x in catalog if x['id'] == 'custom-status'],
                         ['widget:right:0', 'widget:right:2'])
        self.assertNotIn('already.disabled', [x['id'] for x in catalog])
        self.assertNotIn('omarchy.bar', [x['id'] for x in catalog])
        self.assertNotIn('NEVER_EXECUTE', result.stdout)

    def test_keep_everything_is_byte_for_byte_noop(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('no settings changed', result.stdout)
        self.assertEqual(self.config.read_bytes(), self.raw)
        self.assertFalse((self.root / '.local/state').exists())

    def test_deselect_plugin_preserves_custom_widget_and_unrelated_settings(self):
        self.env['MOCK_DROP'] = 'Plugin: Example panel'
        result = self.run_script(text='APPLY\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        changed = json.loads(self.config.read_text())
        self.assertEqual(changed['bar']['layout']['right'], [self.custom, dict(self.custom, interval=17)])
        self.assertEqual(changed['disabledPlugins'], ['already.disabled', 'example.panel'])
        self.assertEqual(changed['plugins'], [])
        self.assertEqual(changed['idle'], self.original['idle'])
        self.assertEqual(changed['unrelated'], self.original['unrelated'])
        backups = list((self.root / '.local/state/frankenstein/settings-backups').glob('*.json'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), self.raw)
        self.assertFalse((self.root / 'NEVER_EXECUTE').exists())

    def test_one_custom_instance_can_be_removed_without_changing_other(self):
        self.env['MOCK_DROP'] = 'Widget: custom-status (right #1)'
        result = self.run_script(text='APPLY\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        changed = json.loads(self.config.read_text())
        self.assertEqual(changed['bar']['layout']['right'], [{'id': 'example.panel'}, dict(self.custom, interval=17)])
        self.assertEqual(changed['plugins'], self.original['plugins'])

    def test_cancel_and_decline_do_not_write(self):
        self.env['MOCK_CANCEL'] = '1'
        self.assertEqual(self.run_script().returncode, 0)
        self.env.pop('MOCK_CANCEL')
        self.env['MOCK_DROP'] = 'Plugin: Example panel'
        self.assertEqual(self.run_script(text='NO\n').returncode, 0)
        self.assertEqual(self.config.read_bytes(), self.raw)

    def test_preview_does_not_apply(self):
        keep = self.root / 'keep.json'
        keep.write_text('[]')
        result = self.run_script('--preview', str(keep))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Proposed changes', result.stdout)
        self.assertEqual(self.config.read_bytes(), self.raw)

    def test_invalid_selection_rejected(self):
        keep = self.root / 'keep.json'
        for content in ('["unknown"]', '["widget:right:0","widget:right:0"]', '{}', '[42]'):
            keep.write_text(content)
            self.assertNotEqual(self.run_script('--preview', str(keep)).returncode, 0)
            self.assertEqual(self.config.read_bytes(), self.raw)

    def test_concurrent_edit_preserved(self):
        self.env.update(MOCK_DROP='Plugin: Example panel', MOCK_CONCURRENT='1')
        result = self.run_script(text='APPLY\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('changed during selection', result.stderr)
        self.assertEqual(self.config.read_bytes(), self.raw + b'\n')

    def test_symlink_and_unsupported_configuration_refused(self):
        target = self.config.with_name('original.json')
        self.config.rename(target)
        self.config.symlink_to(target)
        self.assertNotEqual(self.run_script('--list').returncode, 0)
        self.config.unlink()
        self.config.write_text('{}')
        self.assertNotEqual(self.run_script('--list').returncode, 0)
        self.assertEqual(target.read_bytes(), self.raw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
