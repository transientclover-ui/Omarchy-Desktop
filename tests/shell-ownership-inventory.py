#!/usr/bin/env python3
"""Run the offline inventory against disposable fixtures only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/shell-ownership-inventory.py'
UNIT = 'omarchy-shell.service'
TEXT = '[Service]\nExecStart=/usr/bin/quickshell -n -p /usr/share/omarchy/shell\n'


def snapshot(root):
    return {str(p.relative_to(root)): ('link', os.readlink(p)) if p.is_symlink()
            else ('file', p.read_bytes(), p.stat().st_mtime_ns, p.stat().st_mode)
            if p.is_file() else ('dir', p.stat().st_mode)
            for p in root.rglob('*')}


class InventoryTests(unittest.TestCase):
    def test_matrix(self):
        cases = ['enabled', 'disabled', 'comments', 'wrapper', 'duplicate',
                 'environment', 'drop-in', 'alias', 'mask', 'wrong-target',
                 'extra-link', 'autostart', 'other-unit', 'missing-unit',
                 'missing-directory', 'linked-directory', 'fifo', 'invalid-utf8']
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                units = root / 'units'
                units.mkdir()
                autostart = root / 'autostart'
                autostart.mkdir()
                unit = units / UNIT
                unit.write_text(TEXT)
                if case != 'disabled':
                    wants = units / 'graphical-session.target.wants'
                    wants.mkdir()
                    (wants / UNIT).symlink_to('../' + UNIT)
                if case == 'comments':
                    unit.write_text('# fixture\n\n' + TEXT)
                if case in ('wrapper', 'duplicate', 'environment'):
                    unit.write_text({'wrapper': '[Service]\nExecStart=/bin/sh -c touch SHOULD_NOT_EXIST\n',
                                     'duplicate': TEXT + TEXT,
                                     'environment': TEXT + 'Environment=FOO=bar\n'}[case])
                if case == 'drop-in':
                    drop = units / (UNIT + '.d')
                    drop.mkdir()
                    (drop / 'override.conf').write_text('[Service]\nRestart=always\n')
                if case == 'alias':
                    (units / 'alias.service').symlink_to(UNIT)
                if case in ('mask', 'missing-unit', 'invalid-utf8'):
                    unit.unlink()
                    if case == 'mask':
                        unit.symlink_to('/dev/null')
                    elif case == 'invalid-utf8':
                        unit.write_bytes(b'\xff')
                if case == 'wrong-target':
                    link = wants / UNIT
                    link.unlink()
                    link.symlink_to('/outside/' + UNIT)
                if case == 'extra-link':
                    extra = units / 'default.target.wants'
                    extra.mkdir()
                    (extra / UNIT).symlink_to('../' + UNIT)
                if case == 'autostart':
                    (autostart / 'shell.desktop').write_text('[Desktop Entry]\nExec=touch SHOULD_NOT_EXIST\n')
                if case == 'other-unit':
                    (units / 'other.service').write_text(TEXT)
                if case in ('missing-directory', 'linked-directory'):
                    autostart.rmdir()
                    if case == 'linked-directory':
                        autostart.symlink_to(units, target_is_directory=True)
                if case == 'fifo':
                    os.mkfifo(units / 'special')
                # Do not read a FIFO while making the independent before/after snapshot.
                before = snapshot(root) if case != 'fifo' else None
                result = subprocess.run(['python3', str(TOOL), str(root)],
                                        cwd=root, text=True, capture_output=True, timeout=5)
                report = json.loads(result.stdout)
                recognized = case in ('enabled', 'disabled', 'comments')
                self.assertEqual(result.returncode, 0 if recognized else 1, result.stderr)
                self.assertEqual(report['recognized_shape'], recognized)
                self.assertFalse(report['migration_ready'])
                self.assertEqual(bool(report['reasons']), not recognized)
                self.assertFalse((root / 'SHOULD_NOT_EXIST').exists())
                if before is not None:
                    self.assertEqual(before, snapshot(root))
                if recognized:
                    self.assertEqual(report['activation'], 'no-link-in-snapshot' if case == 'disabled'
                                     else 'graphical-session.target')
                    recorded = next(e for e in report['entries'] if e['path'] == 'units/' + UNIT)
                    self.assertEqual(recorded['sha256'], hashlib.sha256(unit.read_bytes()).hexdigest())


if __name__ == '__main__':
    unittest.main()
