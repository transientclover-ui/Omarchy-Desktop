#!/usr/bin/env python3
"""Exercise the owned shell's pure manifest projection without running QML."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'src/frankenstein/omarchy-shell/shell.qml').read_text()
FUNCTION = SOURCE[SOURCE.index('  function publicPluginManifest('):SOURCE.index('  function publicBarConfig(')]

class PluginManifest(unittest.TestCase):
    def check_js(self, body):
        result = subprocess.run(['node', '-'], input="const assert = require('node:assert/strict');\n" + FUNCTION + body,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bundled_script_path_survives_without_host_privileges(self):
        self.check_js('''
const input = {id:'custom.widget', __sourceDir:'/plugin/source', __isFirstParty:false,
               __hostCapabilities:['privileged'], options:{value:3}};
const output = publicPluginManifest(input);
assert.equal(output.__sourceDir + '/script.sh', '/plugin/source/script.sh');
assert.ok(!Object.hasOwn(output, '__isFirstParty'));
assert.ok(!Object.hasOwn(output, '__hostCapabilities'));
output.options.value = 9;
assert.equal(input.options.value, 3);
assert.deepEqual(input.__hostCapabilities, ['privileged']);
''')

    def test_first_party_identity_and_null_are_preserved(self):
        self.check_js('''
const input = {__isFirstParty:true, __hostCapabilities:['trusted']};
assert.equal(publicPluginManifest(input), input);
assert.equal(publicPluginManifest(null), null);
''')

if __name__ == '__main__':
    unittest.main()
