#!/usr/bin/env python3
"""Exercise preserved-shell health decisions without touching user services."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'src/bin/frankenstein-shell-adapter').read_text()
FUNCTION = SOURCE.split('check_preserved_shell() {', 1)[1].split('\n}\n', 1)[0]

class HealthTests(unittest.TestCase):
    def test_health_matrix(self):
        cases = [
            ('one', 'active', 'ok', '[{"pid":123}]', 0, True),
            ('duplicate', 'active', 'ok', '[{"pid":123},{"pid":456}]', 0, False),
            ('none', 'active', 'ok', '[]', 0, False),
            ('invalid', 'active', 'ok', '{}', 0, False),
            ('query-failed', 'active', 'ok', '[]', 1, False),
            ('inactive', 'inactive', 'ok', '[{"pid":123}]', 0, False),
            ('ipc-failed', 'active', '', '[{"pid":123}]', 0, False),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            qs = Path(tmp) / 'qs'
            qs.write_text('#!/bin/sh\nprintf "%s\\n" "$TEST_INSTANCES"\nexit "$TEST_QUERY_STATUS"\n')
            qs.chmod(0o755)
            for name, state, ping, instances, query_status, healthy in cases:
                with self.subTest(name=name):
                    env = dict(os.environ, PATH=tmp + ':' + os.environ['PATH'],
                               TEST_STATE=state, TEST_PING=ping,
                               TEST_INSTANCES=instances, TEST_QUERY_STATUS=str(query_status))
                    script = '''set -euo pipefail
systemctl() { printf '%s\\n' "$TEST_STATE"; }
ipc() { printf '%s\\n' "$TEST_PING"; }
ipc_shell_dir=/usr/share/omarchy/shell
check_preserved_shell() {''' + FUNCTION + '\n}\ncheck_preserved_shell\n'
                    result = subprocess.run(['bash', '-c', script], env=env, text=True, capture_output=True)
                    self.assertEqual(result.returncode == 0, healthy, result.stdout + result.stderr)
                    self.assertIn('plugin_compatibility=not-certified', result.stdout)
                    if name == 'duplicate':
                        self.assertIn('shell_instances=2', result.stdout)
                        self.assertIn('ownership is unresolved', result.stderr)

if __name__ == '__main__':
    unittest.main()
