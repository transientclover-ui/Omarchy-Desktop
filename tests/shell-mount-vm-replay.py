#!/usr/bin/env python3
"""Replay sanitized guest observations; no systemd manager or source paths opened."""
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
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'tests/fixtures/shell-mount/systemd-261'
MODEL = runpy.run_path(str(ROOT / 'tools/shell-mount-context.py'))
SOURCE = '/home/test/.config/systemd/user'
UNIT = 'omarchy-shell.service'


def contents(root):
    return {str(p.relative_to(root)): ('link', os.readlink(p)) if p.is_symlink()
            else (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_symlink() or p.is_file()}


class GuestReplayTests(unittest.TestCase):
    def test_provenance_and_sanitization(self):
        validation = json.loads((FIXTURE / 'validation.json').read_text())
        self.assertEqual(validation['capture_exit'], 0)
        self.assertEqual(validation['comparison_exit'], 1)
        self.assertEqual(validation['evidence_mode'], '0o600')
        self.assertEqual(validation['systemd'], 'systemd 261 (261.2-1-arch)')
        digest = hashlib.sha256((FIXTURE / UNIT).read_bytes()).hexdigest()
        self.assertEqual(validation['unchanged_hashes'][SOURCE + '/' + UNIT], digest)
        for path in FIXTURE.iterdir():
            if path.suffix in ('.json', '.jsonl', '.txt'):
                self.assertNotIn('/home/omarchytest', path.read_text(), str(path))

    def test_typed_reply_replay(self):
        capture = json.loads((FIXTURE / 'capture.json').read_text())
        self.assertTrue(capture['sanitized'])
        self.assertEqual(capture['capture_exit_status'], 0)
        data = (FIXTURE / UNIT).read_bytes()
        self.assertEqual(capture['fragment']['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(capture['fragment']['size_bytes'], len(data))
        before = contents(FIXTURE)
        calls = []
        def run(command, **kwargs):
            self.assertEqual(command[:5], ['busctl', '--user', '--json=short', '--no-pager', 'get-property'])
            self.assertEqual(command[5], MODEL['EFFECTIVE']['DESTINATION'])
            group = next(g for g, (obj, interface, fields) in MODEL['GROUPS'].items()
                         if command[6] == MODEL['PREFIX'] + obj and
                         command[7] == MODEL['EFFECTIVE']['DESTINATION'] + '.' + interface)
            self.assertEqual(command[8:], list(MODEL['GROUPS'][group][2]))
            self.assertEqual(kwargs['timeout'], 5)
            calls.append(group)
            return subprocess.CompletedProcess(command, 0,
                stdout=(FIXTURE / (group + '-raw.jsonl')).read_text(), stderr='')
        with patch.object(subprocess, 'run', side_effect=run):
            context = MODEL['collect']()
        self.assertEqual(calls, list(MODEL['GROUPS']))
        self.assertEqual(context, capture['mount_context'])
        self.assertEqual(sum(len(v) for v in context['properties'].values()), 29)
        self.assertEqual(capture['collector_exit_status'], 0)
        self.assertTrue(capture['effective']['collected'])
        self.assertEqual(contents(FIXTURE), before)

    def test_truncated_actual_replies_refuse(self):
        for missing in MODEL['GROUPS']:
            with self.subTest(group=missing):
                calls = []
                def run(command, **kwargs):
                    group = next(g for g, (obj, interface, fields) in MODEL['GROUPS'].items()
                                 if command[6] == MODEL['PREFIX'] + obj and
                                 command[7].endswith('.' + interface))
                    rows = (FIXTURE / (group + '-raw.jsonl')).read_text().splitlines()
                    calls.append(group)
                    if group == missing:
                        rows = rows[:-1]
                    return subprocess.CompletedProcess(command, 0,
                        stdout=''.join(row + '\n' for row in rows), stderr='')
                with patch.object(subprocess, 'run', side_effect=run):
                    context = MODEL['collect']()
                self.assertEqual(calls, list(MODEL['GROUPS']))
                self.assertFalse(context['collected'])
                self.assertNotIn(missing, context['properties'])
                self.assertEqual(context['errors'], [missing + ' query failed: ValueError'])

    def test_full_comparison_and_mismatch(self):
        original = json.loads((FIXTURE / 'capture.json').read_text())
        for name in ('observed', 'changed-home', 'changed-restart'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                snap = root / 'snapshot'
                units = snap / 'units'
                (units / 'graphical-session.target.wants').mkdir(parents=True)
                (snap / 'autostart').mkdir()
                (units / UNIT).write_bytes((FIXTURE / UNIT).read_bytes())
                (units / UNIT).chmod(0o644)
                (units / 'graphical-session.target.wants').chmod(0o755)
                (units / 'graphical-session.target.wants' / UNIT).symlink_to('../' + UNIT)
                capture = copy.deepcopy(original)
                if name == 'changed-restart':
                    capture['effective']['properties']['Service']['Restart']['data'] = 'always'
                if name == 'changed-home':
                    capture['mount_context']['properties']['HomeMount']['Where']['data'] = '/other'
                evidence = root / 'capture.json'
                evidence.write_text(json.dumps(capture))
                before, fixture_before = contents(root), contents(FIXTURE)
                result = subprocess.run([sys.executable,
                    str(ROOT / 'tools/shell-ownership-inventory.py'), str(snap),
                    '--capture', str(evidence), '--source-unit-directory', SOURCE,
                    '--require-effective', '--mount-home', '/home/test'], capture_output=True, text=True, timeout=5,
                    env=dict(os.environ, PATH='', PYTHONDONTWRITEBYTECODE='1'))
                report = json.loads(result.stdout)
                self.assertEqual(report, json.loads((FIXTURE / (name + '.json')).read_text()))
                self.assertEqual(result.returncode, 0 if report['consistent_observations'] else 1)
                self.assertFalse(report['migration_ready'])
                self.assertTrue(report['fragment_bytes_match'])
                self.assertTrue(report['recognized_shape'])
                self.assertFalse(report['effective_properties_match'])
                if name == 'observed':
                    self.assertTrue(report['mount_context_consistent'])
                    self.assertEqual(report['mount_context_reasons'], [])
                    self.assertEqual(report['reasons'],
                                     ['Effective property differs from retained-vm-v1: After'])
                if name != 'observed':
                    self.assertFalse(report['mount_context_consistent'])
                if name == 'changed-home':
                    self.assertIn('Mount-context disagreement: HomeMount.Where', report['reasons'])
                if name == 'changed-restart':
                    self.assertIn('Effective property differs from retained-vm-v1: Restart', report['reasons'])
                self.assertEqual(contents(root), before)
                self.assertEqual(contents(FIXTURE), fixture_before)


if __name__ == '__main__':
    unittest.main()
