#!/usr/bin/env python3
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('watchdog', str(ROOT / 'src/libexec/frankenstein-watchdog'))
spec = importlib.util.spec_from_loader(loader.name, loader)
w = importlib.util.module_from_spec(spec)
loader.exec_module(w)

class Fake:
    diagnostics = ['plasma-kwin_wayland.service']
    def __init__(self, healthy=False):
        self.healthy = healthy
    def check(self):
        return {'healthy': self.healthy, 'details': 'test'}
    def recovery(self, mode):
        return ['systemctl', '--user', 'restart', w.UNIT]

class Tests(unittest.TestCase):
    def test_healthy_and_once(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, XDG_RUNTIME_DIR=directory):
            root = Path(directory) / 'incidents'
            fake = Fake(True)
            with patch.object(w, 'command') as command:
                self.assertEqual(w.run(root, fake, 'filtered', {'session_id': 'login'}), 0)
                self.assertFalse(root.exists())
                fake.healthy = False
                w.run(root, fake, 'filtered', {'session_id': 'login'})
                command.assert_not_called()
    def test_capture_before_recovery_and_circuit(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, XDG_RUNTIME_DIR=directory), patch.object(w.time, 'sleep'):
            root = Path(directory) / 'incidents'
            actions = []
            def command(args):
                if 'restart' in args:
                    files = list(root.glob('*.json'))
                    record = json.loads(files[0].read_text())
                    self.assertEqual(len(record['failed_checks']), 3)
                    self.assertIn('plasma-kwin_wayland.service', record['journal'])
                    self.assertEqual(record['recovery']['outcome'], 'in-progress')
                    actions.append(args)
                return 0, 'active'
            with patch.object(w, 'command', side_effect=command):
                w.run(root, Fake(), 'filtered', {'session_id': 'login'})
                w.run(root, Fake(), 'filtered', {'session_id': 'login'})
            self.assertEqual(len(actions), 1)
            record = json.loads(next(root.glob('*.json')).read_text())
            self.assertEqual(record['recovery']['outcome'], 'unhealthy')
            self.assertEqual(next(root.glob('*.json')).stat().st_mode & 0o777, 0o600)
    def test_no_recovery_without_evidence(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, XDG_RUNTIME_DIR=directory), patch.object(w.time, 'sleep'), patch.object(w, 'command', return_value=(0, '')), patch.object(w, 'save', side_effect=OSError('disk full')):
            fake = Fake()
            with patch.object(fake, 'recovery') as recovery:
                with self.assertRaises(OSError):
                    w.run(Path(directory) / 'incidents', fake, 'filtered', {'session_id': 'login'})
                recovery.assert_not_called()
    def test_retention(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for i in range(14):
                (root / f'incident-{i:03}.json').write_text('{}')
            (root / 'incident-999.json').write_bytes(b'x' * (w.MAX_BYTES + 1))
            w.prune(root)
            self.assertLessEqual(len(list(root.glob('*.json'))), 10)
            self.assertLessEqual(sum(p.stat().st_size for p in root.glob('*.json')), w.MAX_BYTES * 10)
    def test_privacy_and_adapters(self):
        output = w.redact('token=abc\nAuthorization: Bearer xyz\nhttps://user:pass@example.org\n' + 'a' * 50 + '\nnormal failure')
        for secret in ['abc', 'xyz', 'example.org', 'a' * 50]:
            self.assertNotIn(secret, output)
        self.assertIn('normal failure', output)
        self.assertIsInstance(w.adapter('KDE', 'wayland'), w.Plasma)
        self.assertIsNone(w.adapter('GNOME', 'wayland'))
        self.assertIsNone(w.adapter('KDE', 'x11'))
    def test_preserved_shell_recovery_and_custom_unit_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            unit = Path(directory) / 'omarchy-shell.service'
            unit.write_text('[Service]\nExecStart=/usr/bin/quickshell -n -p /usr/share/omarchy/shell\n')
            def command(args):
                return (0, str(unit)) if '--property=FragmentPath' in args else (0, '')
            with patch.object(w, 'command', side_effect=command):
                self.assertEqual(w.Plasma().recovery('preserve'), ['systemctl', '--user', 'restart', 'omarchy-shell.service'])
                unit.write_text('[Service]\nExecStart=/usr/bin/quickshell -n -p /usr/share/omarchy/shell\nExecStartPost=/usr/bin/systemctl restart plasma-kwin_wayland.service\n')
                self.assertIsNone(w.Plasma().recovery('preserve'))
            with patch.object(w, 'command', side_effect=lambda args: (0, str(unit)) if '--property=FragmentPath' in args else (0, 'override.conf') if '--property=DropInPaths' in args else (0, '')):
                self.assertIsNone(w.Plasma().recovery('preserve'))

    def test_success_keeps_original_failure(self):
        class Recovering(Fake):
            def recovery(self, mode):
                self.healthy = True
                return super().recovery(mode)
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, XDG_RUNTIME_DIR=directory), patch.object(w.time, 'sleep'), patch.object(w, 'command', return_value=(0, 'active')):
            root = Path(directory) / 'incidents'
            w.run(root, Recovering(), 'filtered', {'session_id': 'login'})
            record = json.loads(next(root.glob('*.json')).read_text())
            self.assertEqual(record['recovery']['outcome'], 'healthy')
            self.assertTrue(all(not check['healthy'] for check in record['failed_checks']))

    def test_recovery_allowlist(self):
        with patch.object(w, 'command', return_value=(1, '')), patch.object(Path, 'exists', return_value=False):
            self.assertIsNone(w.Plasma().recovery('preserve'))
            self.assertIsNone(w.Plasma().recovery('filtered'))
        source = (ROOT / 'src/libexec/frankenstein-watchdog').read_text()
        self.assertNotIn("'restart', 'plasma", source)
        self.assertNotIn("'restart', 'hypr", source)
        unit = (ROOT / 'src/systemd/frankenstein-watchdog.service').read_text()
        self.assertIn('Restart=no', unit)

if __name__ == '__main__':
    unittest.main()
