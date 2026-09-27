#!/usr/bin/env python3
"""Replay actual repeated guest observations without contacting a manager."""
import copy
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/shell-coherence/systemd-261'
MODEL = runpy.run_path(str(ROOT / 'tools/shell-capture-coherence.py'))
UNIT = 'omarchy-shell.service'
SOURCE = '/home/test/.config/systemd/user'


def read(name):
    return json.loads((FIXTURE / (name + '.json')).read_text())


class GuestCoherenceReplay(unittest.TestCase):
    def test_actual_change_and_restoration(self):
        validation = read('validation')
        digest = hashlib.sha256((FIXTURE / UNIT).read_bytes()).hexdigest()
        self.assertEqual(validation['before_hashes'][SOURCE + '/' + UNIT], digest)
        self.assertEqual(validation['before_hashes'], validation['restored_hashes'])
        self.assertEqual(validation['cases']['stable']['hashes_after'], validation['before_hashes'])
        self.assertEqual(validation['systemd'], 'systemd 261 (261.2-1-arch)')
        for name in ('stable', 'changed'):
            case = validation['cases'][name]
            self.assertEqual(case['evidence_mode'], '0o600')
            self.assertEqual(case['capture_exit'], 0 if name == 'stable' else 1)
            self.assertEqual(case['comparison_exit'], 1)
        changed = read('changed')
        after = changed['coherence']['after']
        appended = (FIXTURE / UNIT).read_bytes() + b'\n# Disposable coherence validation change\n'
        self.assertEqual(after['fragment']['sha256'], hashlib.sha256(appended).hexdigest())
        self.assertEqual(after['fragment']['size_bytes'], len(appended))
        self.assertEqual(changed['report']['unit']['NeedDaemonReload'], 'no')
        self.assertEqual(after['report']['unit']['NeedDaemonReload'], 'yes')
        self.assertEqual(read('mutation')['action'], 'append comment after first RootMount reply')
        for file in FIXTURE.glob('*.json'):
            self.assertNotIn('/home/omarchytest', file.read_text())

    def test_recompute_real_coherence_and_reject_forgery(self):
        self.assertEqual(MODEL['assess'](read('stable')), [])
        changed = read('changed')
        self.assertEqual(MODEL['assess'](changed), changed['coherence']['errors'])
        self.assertIn('Observation changed: fragment', MODEL['assess'](changed))
        forged = copy.deepcopy(changed)
        forged['coherence'].update(agrees=True, errors=[])
        self.assertEqual(MODEL['assess'](forged), ['Capture coherence derived fields disagree with observations'])

    def test_full_offline_comparisons(self):
        fixture_before = {p.name: p.read_bytes() for p in FIXTURE.iterdir() if p.is_file()}
        with tempfile.TemporaryDirectory() as temp:
            snap = Path(temp) / 'snapshot'
            units = snap / 'units'
            (units / 'graphical-session.target.wants').mkdir(parents=True)
            (snap / 'autostart').mkdir()
            (units / UNIT).write_bytes((FIXTURE / UNIT).read_bytes())
            (units / UNIT).chmod(0o644)
            (units / 'graphical-session.target.wants').chmod(0o755)
            (units / 'graphical-session.target.wants' / UNIT).symlink_to('../' + UNIT)
            for name in ('stable', 'changed'):
                for require in (False, True):
                    with self.subTest(name=name, require=require):
                        result = subprocess.run([sys.executable, str(ROOT / 'tools/shell-ownership-inventory.py'), str(snap), '--capture', str(FIXTURE / (name + '.json')), '--source-unit-directory', SOURCE, '--require-effective', '--mount-home', '/home/test'] + (['--require-coherence'] if require else []), capture_output=True, text=True, timeout=5, env=dict(os.environ, PATH='', PYTHONDONTWRITEBYTECODE='1'))
                        self.assertEqual(result.returncode, 1, result.stderr)
                        report = json.loads(result.stdout)
                        self.assertEqual(report, read(name + '-comparison'))
                        self.assertIs(report['capture_coherence_agrees'], name == 'stable')
                        self.assertFalse(report['migration_ready'])
                        self.assertFalse(report['consistent_observations'])
                        self.assertIn('Effective property differs from retained-vm-v1: After', report['reasons'])
                        if name == 'stable':
                            self.assertEqual(report['reasons'], ['Effective property differs from retained-vm-v1: After'])
                            self.assertTrue(report['mount_context_consistent'])
                            self.assertTrue(report['fragment_bytes_match'])
                        else:
                            self.assertIn('Observation changed: fragment', report['reasons'])
        self.assertEqual(fixture_before, {p.name: p.read_bytes() for p in FIXTURE.iterdir() if p.is_file()})


if __name__ == '__main__':
    unittest.main()
