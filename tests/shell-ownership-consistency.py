#!/usr/bin/env python3
"""Offline cross-checks with disposable snapshots and captured-property fixtures."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/shell-ownership-inventory.py'
FIXTURES = ROOT / 'tests/fixtures/shell-metadata'
SOURCE = '/home/test/.config/systemd/user'
UNIT = 'omarchy-shell.service'
COMMAND = '/usr/bin/quickshell -n -p /usr/share/omarchy/shell'


def contents(root):
    return {str(p.relative_to(root)): ('link', os.readlink(p)) if p.is_symlink()
            else ('directory',) if p.is_dir()
            else (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns)
            for p in root.rglob('*')}


class ConsistencyTests(unittest.TestCase):
    def test_matrix(self):
        cases = ['active', 'inactive', 'restart-attempt', 'disabled', 'fragment',
                 'search-path', 'exec-wrapper', 'extra-exec', 'ignore-errors',
                 'enabled-without-link', 'disabled-with-link', 'snapshot-wrapper',
                 'snapshot-drop-in', 'metadata-drop-in', 'metadata-stale',
                 'forged-derived', 'missing-property', 'wrong-type', 'list-report',
                 'null-envelope', 'failed-capture', 'malformed-json', 'linked-capture',
                 'relative-source', 'traversal-source', 'unnormalized-source',
                 'duplicate-json', 'numeric-flag', 'hash-match', 'hash-mismatch',
                 'hash-comment', 'hash-refused', 'hash-path', 'hash-size',
                 'hash-type', 'hash-exit']
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                snap = root / 'snapshot'
                units = snap / 'units'
                units.mkdir(parents=True)
                (snap / 'autostart').mkdir()
                (units / UNIT).write_text('[Service]\nExecStart=' + COMMAND + '\n')
                wants = units / 'graphical-session.target.wants'
                wants.mkdir()
                link = wants / UNIT
                link.symlink_to('../' + UNIT)
                fixture = case if case in ('inactive', 'restart-attempt') else 'active'
                capture = json.loads((FIXTURES / ('systemd-261-capture-' + fixture + '.json')).read_text())
                unit = capture['report']['unit']
                source = SOURCE
                if case == 'disabled':
                    unit['UnitFileState'] = 'disabled'
                    link.unlink()
                elif case == 'fragment':
                    unit['FragmentPath'] = '/etc/systemd/user/' + UNIT
                elif case == 'search-path':
                    capture['report']['search_paths'].remove(SOURCE)
                    capture['report']['manager']['UnitPath'] = ' '.join(capture['report']['search_paths'])
                elif case == 'exec-wrapper':
                    unit['ExecStart'] = unit['ExecStart'].replace(COMMAND, '/bin/sh -c touch SHOULD_NOT_EXIST')
                elif case == 'extra-exec':
                    unit['ExecStart'] += ' ' + unit['ExecStart']
                elif case == 'ignore-errors':
                    unit['ExecStart'] = unit['ExecStart'].replace('ignore_errors=no', 'ignore_errors=yes')
                elif case == 'enabled-without-link':
                    link.unlink()
                elif case == 'disabled-with-link':
                    unit['UnitFileState'] = 'disabled'
                elif case == 'snapshot-wrapper':
                    (units / UNIT).write_text('[Service]\nExecStart=/bin/sh -c touch SHOULD_NOT_EXIST\n')
                elif case == 'snapshot-drop-in':
                    (units / (UNIT + '.d')).mkdir()
                elif case == 'metadata-drop-in':
                    unit['DropInPaths'] = '/override.conf'
                    capture['report']['reasons'] = ['Drop-ins require review']
                elif case == 'metadata-stale':
                    unit['NeedDaemonReload'] = 'yes'
                    capture['report']['reasons'] = ['Manager configuration may be stale']
                elif case == 'forged-derived':
                    capture['report']['migration_ready'] = True
                elif case == 'numeric-flag':
                    capture['report']['metadata_collected'] = 1
                elif case == 'missing-property':
                    del unit['Names']
                elif case == 'wrong-type':
                    unit['Names'] = []
                elif case == 'list-report':
                    capture['report'] = []
                elif case == 'null-envelope':
                    capture = None
                elif case == 'failed-capture':
                    capture['collector_exit_status'] = 1
                elif case == 'relative-source':
                    source = 'home/test'
                elif case == 'traversal-source':
                    source = '/home/test/../test/.config/systemd/user'
                elif case == 'unnormalized-source':
                    source = SOURCE + '/'
                if case.startswith('hash-'):
                    data = (units / UNIT).read_bytes()
                    capture['capture_exit_status'] = 0
                    capture['fragment'] = {'path': unit['FragmentPath'], 'outcome': 'ok',
                                           'sha256': hashlib.sha256(data).hexdigest(),
                                           'size_bytes': len(data)}
                    if case == 'hash-mismatch':
                        capture['fragment']['sha256'] = '0' * 64
                    elif case == 'hash-comment':
                        (units / UNIT).write_bytes(b'# valid shape, different bytes\n' + data)
                    elif case == 'hash-refused':
                        capture['fragment'] = {'outcome': 'refused', 'reason': 'changed-during-read'}
                    elif case == 'hash-path':
                        capture['fragment']['path'] = '/other/unit'
                    elif case == 'hash-size':
                        capture['fragment']['size_bytes'] += 1
                    elif case == 'hash-type':
                        capture['fragment']['size_bytes'] = str(len(data))
                    elif case == 'hash-exit':
                        capture['capture_exit_status'] = 1
                path = root / 'capture.json'
                path.write_text('{' if case == 'malformed-json' else json.dumps(capture))
                if case == 'duplicate-json':
                    path.write_text(path.read_text().replace('"schema": 1', '"schema": 2, "schema": 1', 1))
                if case == 'linked-capture':
                    path.rename(root / 'actual.json')
                    path.symlink_to(root / 'actual.json')
                before = contents(root)
                # Empty PATH ensures this route cannot accidentally call host systemctl.
                result = subprocess.run([sys.executable, str(TOOL), str(snap), '--capture',
                                         str(path), '--source-unit-directory', source],
                                        env=dict(os.environ, PATH='', PYTHONDONTWRITEBYTECODE='1'),
                                        cwd=root, text=True, capture_output=True, timeout=5)
                report = json.loads(result.stdout)
                expected = case in ('active', 'inactive', 'restart-attempt', 'disabled', 'hash-match')
                self.assertEqual(result.returncode, 0 if expected else 1, result.stderr)
                self.assertEqual(report['consistent_observations'], expected)
                self.assertFalse(report['migration_ready'])
                self.assertEqual(report['fragment_bytes_match'],
                                 case == 'hash-match' if case.startswith('hash-') else None)
                self.assertEqual(bool(report['reasons']), not expected)
                self.assertEqual(contents(root), before)
                self.assertFalse((root / 'SHOULD_NOT_EXIST').exists())

    def test_vm_fragment_observations(self):
        fixtures = FIXTURES / 'fragment-261'
        capture = fixtures / 'capture.json'
        evidence = json.loads(capture.read_text())
        original = (fixtures / UNIT).read_bytes()
        self.assertEqual(evidence['fragment']['sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(evidence['fragment']['size_bytes'], len(original))
        self.assertEqual(evidence['capture_exit_status'], 0)
        self.assertTrue(evidence['sanitized'])
        for name in ('match', 'different-bytes'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                snap = Path(tmp)
                units = snap / 'units'
                wants = units / 'graphical-session.target.wants'
                wants.mkdir(parents=True)
                wants.chmod(0o755)
                (snap / 'autostart').mkdir()
                data = original if name == 'match' else b'# Comparison-only comment\n' + original
                (units / UNIT).write_bytes(data)
                (units / UNIT).chmod(0o644)
                (wants / UNIT).symlink_to('../' + UNIT)
                before = contents(snap)
                fixture_before = contents(fixtures)
                result = subprocess.run(
                    [sys.executable, str(TOOL), str(snap), '--capture', str(capture),
                     '--source-unit-directory', SOURCE],
                    env=dict(os.environ, PATH='', PYTHONDONTWRITEBYTECODE='1'),
                    text=True, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 0 if name == 'match' else 1, result.stderr)
                report = json.loads(result.stdout)
                # Retain the earlier VM reports unchanged; only shape recognition
                # and its dependent fields differ in the current offline replay.
                expected = json.loads((fixtures / (name + '.json')).read_text())
                expected['reasons'].remove('Unit is outside the recognized direct-launch fixture shape')
                expected['recognized_shape'] = True
                expected['consistent_observations'] = name == 'match'
                expected['launch_command'] = '/usr/bin/quickshell -n -p /usr/share/omarchy/shell'
                self.assertEqual(report, expected)
                # Shape recognition must not bypass mismatched fragment bytes.
                self.assertEqual(report['fragment_bytes_match'], name == 'match')
                self.assertTrue(report['recognized_shape'])
                self.assertEqual(report['consistent_observations'], name == 'match')
                self.assertFalse(report['migration_ready'])
                self.assertEqual(contents(snap), before)
                self.assertEqual(contents(fixtures), fixture_before)

    def test_options_must_be_paired(self):
        for args in (['--capture', '/absent'], ['--source-unit-directory', SOURCE]):
            result = subprocess.run([sys.executable, str(TOOL), '/absent', *args],
                                    text=True, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('must be supplied together', result.stderr)


if __name__ == '__main__':
    unittest.main()
