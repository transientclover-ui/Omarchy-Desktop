#!/usr/bin/env python3
"""Exercise retained workaround only in a disposable directory with a closed PATH.

This is evidence regression, not protection enable/disable or hardware validation.
"""
import json
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

FIXTURE = Path(__file__).resolve().parent / 'fixtures/display-power-cycle/host-20260926'


class WorkaroundEvidenceTests(unittest.TestCase):
    def run_fixture(self, status='connected', home=True, legacy_actions=False, rule_environment=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            commands = root / 'bin'
            commands.mkdir()
            # Closed PATH: never resolve host systemctl, qdbus or display tools.
            for name in ('date', 'tee', 'mkdir', 'dirname', 'cat'):
                (commands / name).symlink_to(shutil.which(name))
            (commands / 'sleep').write_text('#!/bin/sh\nexit 0\n')
            (commands / 'sleep').chmod(0o755)
            (commands / 'whoami').write_text('#!/bin/sh\nprintf \"test\\n\"\n')
            (commands / 'whoami').chmod(0o755)
            calls = root / 'calls'
            def stub(name, body):
                path = commands / name
                path.write_text('#!/bin/sh\nprintf "%s\\n" "' + name + ' $*" >> "$CALLS"\n' + body + '\n')
                path.chmod(0o755)
            stub('systemctl', 'exit ' + ('0' if legacy_actions else '3'))
            # Real host has these names, which the retained script never calls.
            stub('kscreen-doctor', 'exit 99')
            stub('qdbus6', 'exit 99')
            connector = root / 'connector'
            connector.mkdir()
            (connector / 'status').write_text(status + '\n')
            if legacy_actions:
                (connector / 'power_mode').write_text('off\n')
            source = (FIXTURE / 'recover-tv-display.sh.txt').read_text()
            self.assertEqual(source.count('/sys/class/drm/card1-HDMI-A-1'), 1)
            script = root / 'replay.sh'
            script.write_text(source.replace('/sys/class/drm/card1-HDMI-A-1', str(connector)))
            env = {'PATH': str(commands), 'CALLS': str(calls), 'LC_ALL': 'C'}
            if rule_environment:
                self.assertEqual(set(rule_environment), {'DISPLAY', 'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS'})
                env.update(rule_environment)
            if home:
                env['HOME'] = str(root / 'home')
            result = subprocess.run(['/bin/bash', str(script)], env=env, cwd=root,
                                    capture_output=True, text=True, timeout=5)
            actions = calls.read_text().splitlines() if calls.exists() else []
            power = (connector / 'power_mode').read_text() if legacy_actions else None
            return result, actions, power

    def test_missing_home_fails_before_any_action(self):
        result, actions, _ = self.run_fixture(home=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('HOME: unbound variable', result.stderr)
        self.assertEqual(actions, [])

    def test_supplied_udev_environment_does_not_fix_missing_home(self):
        rule = (FIXTURE / 'active-rule.user-supplied.txt').read_text()
        values = dict(re.findall(r'ENV\{([A-Z_]+)\}="([^"]*)"', rule))
        result, actions, _ = self.run_fixture(home=False, rule_environment=values)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('HOME: unbound variable', result.stderr)
        self.assertEqual(actions, [])

    def test_connected_does_not_prove_recovery(self):
        result, actions, _ = self.run_fixture()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SUCCESS:', result.stdout)
        self.assertIn('kscreen_doctor not available', result.stdout)
        self.assertEqual(actions, ['systemctl --user is-active plasmashell'])

    def test_disconnected_still_exits_zero(self):
        result, actions, _ = self.run_fixture(status='disconnected')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('WARNING:', result.stdout)
        self.assertEqual(actions, ['systemctl --user is-active plasmashell'])

    def test_legacy_gated_actions_only_touch_fakes(self):
        result, actions, power = self.run_fixture(legacy_actions=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(power, 'on\n')
        self.assertEqual(actions, ['systemctl --user is-active plasmashell',
                                   'systemctl --user restart plasmashell'])

    def test_evidence_keeps_provenance_and_unproven_status(self):
        observation = json.loads((FIXTURE / 'observation.json').read_text())
        self.assertFalse(observation['integration_ready'])
        self.assertTrue(observation['active_rule_provided'])
        active = (FIXTURE / 'active-rule.user-supplied.txt').read_text()
        copied = (FIXTURE / 'user-copy.rules.txt').read_text()
        self.assertIn('ENV{DBUS_SESSION_BUS_ADDRESS}', active)
        self.assertIn('ENV DBUS_SESSION_BUS_ADDRESS', copied)
        self.assertNotIn('ENV{HOME}', active)
        self.assertIn('/usr/bin/systemd-cat', active)
        self.assertNotIn('systemctl', active)
        for path in FIXTURE.iterdir():
            if path.suffix in ('.json', '.txt'):
                self.assertNotIn('/home/violet', path.read_text())


if __name__ == '__main__':
    unittest.main()
