#!/usr/bin/env python3
"""Exercise capture and real CLI parsing with a fake systemctl, never host services."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / 'tools/capture-shell-ownership-metadata.py'
UNIT = '''Id=omarchy-shell.service
Names=omarchy-shell.service
LoadState=loaded
UnitFileState=enabled
FragmentPath=/home/test/.config/systemd/user/omarchy-shell.service
SourcePath=
DropInPaths=
ActiveState=active
SubState=running
NeedDaemonReload=no
ExecStart={ path=/usr/bin/quickshell ; argv[]=/usr/bin/quickshell -n -p /usr/share/omarchy/shell ; }
'''


class CaptureTests(unittest.TestCase):
    def test_capture_matrix(self):
        for case in ('active', 'inactive', 'drop-in', 'query-failure', 'malformed',
                     'existing-file', 'symlink', 'missing-parent'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                command = root / 'systemctl'
                command.write_text('#!' + sys.executable + '''
import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['AUDIT'], 'a') as stream:
    stream.write(json.dumps(args) + '\\n')
assert args[:4] == ['--user', '--no-pager', 'show', '--all']
assert args[4].startswith('--property=')
assert len(args) in (5, 6)
assert len(args) == 5 or args[5] == 'omarchy-shell.service'
if os.environ['CASE'] == 'query-failure':
    sys.exit(1)
print(os.environ['UNIT'].rstrip('\\n') if len(args) == 6 else 'UnitPath=/home/test/.config/systemd/user /usr/lib/systemd/user')
''')
                command.chmod(0o700)
                unit = UNIT
                if case == 'inactive':
                    unit = unit.replace('enabled', 'disabled').replace('ActiveState=active', 'ActiveState=inactive').replace('SubState=running', 'SubState=dead')
                if case == 'drop-in':
                    unit = unit.replace('DropInPaths=', 'DropInPaths=/override.conf')
                if case == 'malformed':
                    unit += 'Id=duplicate\n'
                output = root / 'evidence.json'
                if case == 'existing-file':
                    output.write_text('keep')
                if case == 'symlink':
                    (root / 'target').write_text('keep')
                    output.symlink_to(root / 'target')
                if case == 'missing-parent':
                    output = root / 'absent/evidence.json'
                result = subprocess.run([sys.executable, str(CAPTURE), str(output)],
                                        env=dict(os.environ, PATH=str(root), CASE=case,
                                                 UNIT=unit, AUDIT=str(root / 'audit')),
                                        text=True, capture_output=True, timeout=20)
                calls = [json.loads(line) for line in (root / 'audit').read_text().splitlines()]
                self.assertEqual(len(calls), 2)
                self.assertEqual(calls[0][-1], 'omarchy-shell.service')
                self.assertEqual(calls[1][-1], '--property=UnitPath')
                if case in ('existing-file', 'symlink', 'missing-parent'):
                    self.assertEqual(result.returncode, 2, result.stderr)
                    if case != 'missing-parent':
                        self.assertEqual(output.read_text(), 'keep')
                    continue
                expected = 0 if case in ('active', 'inactive') else 1
                self.assertEqual(result.returncode, expected, result.stderr)
                evidence = json.loads(output.read_text())
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                self.assertFalse(evidence['sanitized'])
                self.assertFalse(evidence['report']['migration_ready'])
                self.assertEqual(evidence['collector_exit_status'], expected)
                self.assertEqual(evidence['report']['metadata_collected'],
                                 case not in ('query-failure', 'malformed'))


if __name__ == '__main__':
    unittest.main()
