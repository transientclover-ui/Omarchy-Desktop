#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Synthetic policy tests, not runtime tests of the represented software stacks."""
import copy
import hashlib
import itertools
import json
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'src/bin/frankenstein-compatibility'
MODEL = runpy.run_path(str(SCRIPT))
POLICY = json.loads((ROOT / 'src/frankenstein/compatibility/omarchy.json').read_text())
CURRENT = POLICY['validated_stacks'][0]['versions']


class Compatibility(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.shell = self.root / 'usr/share/omarchy/shell'
        self.shell.mkdir(parents=True)
        (self.shell / 'shell.qml').write_text('synthetic contract')
        self.policy = copy.deepcopy(POLICY)
        self.policy['capabilities'] = {}
        self.policy['shell_contracts'][0]['files'] = {
            'shell.qml': hashlib.sha256(b'synthetic contract').hexdigest()}
        for requirement in self.policy['capabilities'].values():
            path = self.root / requirement['path']
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text('\n'.join(requirement['symbols']))
        self.versions = dict(CURRENT)

    def report(self):
        return MODEL['inspect'](self.root, self.versions, self.policy)

    def test_current_known_contract(self):
        self.assertEqual(self.report()['integrations']['filtered-shell']['state'], 'supported')

    def test_thirtytwo_candidate_combinations_are_not_runtime_validation(self):
        # 2 Omarchy x 2 Plasma x 2 Qt base x 2 Qt declarative x 2 Quickshell.
        for omarchy, plasma, base, declarative, qs in itertools.product(
                ['4.0.4-1', '4.0.5-1'], ['6.7.4-3', '6.8.0-1'],
                ['6.11.2', '6.12.0'], ['6.11.2', '6.12.0'], ['0.3.1-1', '0.3.2-1']):
            with self.subTest(omarchy=omarchy, plasma=plasma, base=base, declarative=declarative, qs=qs):
                self.versions = dict(zip(MODEL['PACKAGES'],
                    [omarchy, plasma, base + '-3', declarative + '-1', qs]))
                report = self.report()
                self.assertTrue(report['runtime_in_candidate_matrix'])
                self.assertTrue(report['omarchy_release_in_candidate_matrix'])
                validated = self.versions == CURRENT
                self.assertEqual(report['runtime_validation'] == 'validated-current', validated)
                self.assertEqual(report['integrations']['filtered-shell']['state'] == 'supported', validated)

    def test_missing_unknown_and_git_runtime_versions_disable_filtered(self):
        for package in MODEL['PACKAGES']:
            for value in (None, 'unknown', '999.0-1', '0.3.2.r7.g2b4501a-1'):
                with self.subTest(package=package, value=value):
                    self.versions = dict(CURRENT, **{package: value})
                    report = self.report()
                    self.assertEqual(report['integrations']['filtered-shell']['state'], 'disabled')
                    self.assertTrue(report['diagnostics'])

    def test_added_changed_and_removed_sources_disable_only_adapter(self):
        for mutation in ('changed', 'added', 'removed'):
            with self.subTest(mutation=mutation):
                (self.shell / 'shell.qml').write_text('synthetic contract')
                if mutation == 'changed':
                    (self.shell / 'shell.qml').write_text('different')
                elif mutation == 'added':
                    (self.shell / 'new.qml').write_text('new')
                else:
                    (self.shell / 'shell.qml').unlink()
                report = self.report()
                self.assertEqual(report['shell_contract'], 'unknown')
                self.assertEqual(report['integrations']['filtered-shell']['state'], 'disabled')
                self.assertEqual(report['integrations']['preserved-shell']['state'], 'external')
                (self.shell / 'new.qml').unlink(missing_ok=True)

    def test_offline_cli_refuses_and_changes_no_files(self):
        for relative, content in (
                ('usr/share/frankenstein/compatibility/omarchy.json', self.policy),
                ('var/lib/frankenstein/compat-versions.json', dict(CURRENT, omarchy='4.0.5-1'))):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(content))
        def snapshot():
            return {str(p): (p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_mode)
                    for p in self.root.rglob('*') if p.is_file()}
        before = snapshot()
        result = subprocess.run([str(SCRIPT), 'require', 'filtered-shell', '--root', str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 78)
        self.assertIn('not been validated', result.stderr)
        self.assertEqual(before, snapshot())
        (self.root / 'usr/share/frankenstein/compatibility/omarchy.json').write_text('{broken')
        result = subprocess.run([str(SCRIPT), '--root', str(self.root)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 78)

    def test_gate_precedes_filtered_launch_and_prevents_restart_loop(self):
        source = (ROOT / 'src/bin/frankenstein-shell-adapter').read_text()
        run = source[source.index('run_shell() {'):source.index('ipc() {')]
        self.assertLess(run.index('require filtered-shell'), run.index('exec quickshell'))
        self.assertIn('return 0', run)
        self.assertIn('RestartPreventExitStatus=78',
                      (ROOT / 'src/systemd/frankenstein-omarchy-shell.service').read_text())

    def test_unknown_stack_does_not_launch_with_an_older_restart_policy(self):
        checker = self.root / 'checker'
        checker.write_text('#!/bin/sh\necho "Unknown stack: integration disabled" >&2\nexit 78\n')
        checker.chmod(0o755)
        source = (ROOT / 'src/bin/frankenstein-shell-adapter').read_text()
        run = source[source.index('run_shell() {'):source.index('ipc() {')]
        run = run.replace('compatibility=$(dirname -- "${BASH_SOURCE[0]}")/frankenstein-compatibility',
                          'compatibility=' + str(checker))
        marker = self.root / 'launched'
        result = subprocess.run(['bash', '-c', 'set -euo pipefail\n' + run +
                                 f'\nquickshell() {{ touch {marker}; }}\nrun_shell plasma'],
                                capture_output=True, text=True)
        # An old Restart=on-failure service now stays inactive without a loop.
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('integration disabled', result.stderr)
        self.assertFalse(marker.exists())

    def test_missing_capabilities_have_specific_diagnostics(self):
        self.policy['capabilities'] = copy.deepcopy(POLICY['capabilities'])
        report = self.report()
        self.assertEqual(report['integrations']['filtered-shell']['state'], 'disabled')
        for name in self.policy['capabilities']:
            self.assertEqual(report['capabilities'][name]['state'], 'unavailable')
            self.assertTrue(any(name in message for message in report['diagnostics']))

    def test_versions(self):
        self.assertEqual(MODEL['version']('2:4.0.5-2'), '4.0.5')
        for bad in ('', 'v4.0.5', '4.0.5;sh', '0.3.2.r7.g2b4501a-1'):
            self.assertIsNone(MODEL['version'](bad))


if __name__ == '__main__':
    unittest.main()
