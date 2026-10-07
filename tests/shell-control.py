#!/usr/bin/env python3
"""Exercise explicit shell control without changing any host services."""
from pathlib import Path
import subprocess
import unittest
SOURCE = (Path(__file__).resolve().parents[1] / 'src/bin/frankenstein-shell-adapter').read_text()
DISPATCH = SOURCE[SOURCE.index('shell_mode=$(installed_shell_mode)'):SOURCE.index('ipc_shell_dir=$shell_dir')]
class Control(unittest.TestCase):
    def run_control(self, mode, action, state='active', failure=False):
        mock = '''set -euo pipefail
service=frankenstein-omarchy-shell.service
installed_shell_mode() { echo "$TEST_MODE"; }
systemctl() { if [[ $* == *is-active* ]]; then echo "$TEST_STATE"; else echo "$*"; fi; return "$TEST_FAILURE"; }
'''
        import os
        env = dict(os.environ, TEST_MODE=mode, TEST_STATE=state, TEST_FAILURE='1' if failure else '0')
        return subprocess.run(['bash','-c',mock + DISPATCH + '\nprintf "next=%s\\n" "$1"','test',action],env=env,capture_output=True,text=True)
    def test_preserved_persistent_toggle(self):
        for action, expected in [('shell-enable','enable'),('shell-disable','disable')]:
            result = self.run_control('preserve',action)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(result.stdout.strip(),f'--user {expected} --now omarchy-shell.service')
    def test_filtered_uses_existing_controls(self):
        for action, expected in [('shell-enable','enable'),('shell-disable','disable')]:
            self.assertEqual(self.run_control('filtered',action).stdout.strip(),f'next={expected}')
    def test_status_and_mode(self):
        self.assertEqual(self.run_control('preserve','shell-mode').stdout.strip(),'preserve')
        for state in ('inactive','failed'):
            self.assertEqual(self.run_control('preserve','shell-status',state,True).stdout.strip(),'inactive')
        self.assertNotEqual(self.run_control('preserve','shell-status','unknown',True).returncode,0)
    def test_errors_propagate(self):
        self.assertNotEqual(self.run_control('preserve','shell-enable',failure=True).returncode,0)
if __name__=='__main__': unittest.main()
