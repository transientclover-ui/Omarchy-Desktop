#!/usr/bin/env python3
"""Hash only disposable fragment files; inject replacement and I/O failures."""
import errno
import hashlib
import os
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
API = runpy.run_path(str(ROOT / 'tools/capture-shell-ownership-metadata.py'))
read_fragment = API['fragment_provenance']


class FragmentTests(unittest.TestCase):
    def test_regular_and_refusals(self):
        for case in ('regular', 'empty', 'missing', 'symlink', 'parent-link',
                     'directory', 'fifo', 'oversized', 'relative', 'traversal', 'invalid'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                path = root / 'unit'
                data = b'[Service]\nExecStart=/usr/bin/true\n'
                path.write_bytes(data)
                if case == 'empty':
                    data = b''
                    path.write_bytes(data)
                elif case == 'missing':
                    path.unlink()
                elif case == 'symlink':
                    path.rename(root / 'target')
                    path.symlink_to(root / 'target')
                elif case == 'parent-link':
                    (root / 'alias').symlink_to(root, target_is_directory=True)
                    path = root / 'alias/unit'
                elif case in ('directory', 'fifo'):
                    path.unlink()
                    path.mkdir() if case == 'directory' else os.mkfifo(path)
                elif case == 'oversized':
                    with path.open('wb') as stream:
                        stream.truncate(API['MAX_FRAGMENT_BYTES'] + 1)
                argument = str(path)
                if case == 'relative':
                    argument = 'unit'
                elif case == 'traversal':
                    argument = str(root) + '/../' + root.name + '/unit'
                elif case == 'invalid':
                    argument = None
                report = read_fragment(argument)
                if case in ('regular', 'empty'):
                    self.assertEqual(report['outcome'], 'ok')
                    self.assertEqual(report['sha256'], hashlib.sha256(data).hexdigest())
                    self.assertEqual(report['size_bytes'], len(data))
                    self.assertEqual(path.read_bytes(), data)
                else:
                    self.assertEqual(report['outcome'], 'refused')
                    self.assertNotIn('sha256', report)

    def test_changes_and_errors(self):
        for case in ('replace', 'rewrite', 'parent-replace', 'io-error', 'permission'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp) / 'parent'
                directory.mkdir()
                path = directory / 'unit'
                path.write_bytes(b'original')
                original_read = os.read
                changed = False
                def read(fd, size):
                    nonlocal changed
                    data = original_read(fd, size)
                    if data and not changed:
                        changed = True
                        if case == 'replace':
                            replacement = directory / 'replacement'
                            replacement.write_bytes(b'original')
                            replacement.replace(path)
                        elif case == 'rewrite':
                            path.write_bytes(b'changed!')
                        elif case == 'parent-replace':
                            directory.rename(Path(tmp) / 'old-parent')
                            directory.mkdir()
                            path.write_bytes(b'original')
                        elif case == 'io-error':
                            raise OSError(errno.EIO, 'injected')
                    return data
                if case == 'permission':
                    with patch.object(os, 'open', side_effect=PermissionError(errno.EACCES, 'injected')):
                        report = read_fragment(str(path))
                else:
                    with patch.object(os, 'read', side_effect=read):
                        report = read_fragment(str(path))
                self.assertEqual(report['outcome'], 'refused')
                self.assertNotIn('sha256', report)
                if case in ('replace', 'rewrite', 'parent-replace'):
                    self.assertEqual(report['reason'], 'changed-during-read')


if __name__ == '__main__':
    unittest.main()
