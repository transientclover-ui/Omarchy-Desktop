#!/usr/bin/env python3
"""Mock all manager queries; never contact host systemd."""
import importlib.util
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('metadata', ROOT / 'tools/shell-ownership-metadata.py')
metadata = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metadata)
BASE = dict(Id=metadata.UNIT, Names=metadata.UNIT, LoadState='loaded',
            UnitFileState='enabled', FragmentPath='/home/test/.config/systemd/user/' + metadata.UNIT,
            SourcePath='', DropInPaths='', ActiveState='active', SubState='running',
            NeedDaemonReload='no', ExecStart='{ path=/usr/bin/quickshell ; argv[]=/usr/bin/quickshell -n -p /usr/share/omarchy/shell ; }')
PATHS = '/home/test/.config/systemd/user /etc/systemd/user /usr/lib/systemd/user'


def output(values):
    return ''.join(key + '=' + value + '\n' for key, value in values.items())


class MetadataTests(unittest.TestCase):
    def collect(self, unit=None, manager=None, failure=None):
        calls = []
        def run(command, **kwargs):
            calls.append(command)
            self.assertEqual(command[:5], ['systemctl', '--user', '--no-pager', 'show', '--all'])
            self.assertEqual(kwargs['timeout'], 5)
            self.assertTrue(kwargs['check'])
            self.assertNotIn('shell', kwargs)
            is_unit = command[-1] == metadata.UNIT
            expected = metadata.PROPERTIES if is_unit else ('UnitPath',)
            self.assertEqual(command[5], '--property=' + ','.join(expected))
            self.assertEqual(len(command), 7 if is_unit else 6)
            if failure and (is_unit == failure[0]):
                raise failure[1]
            text = (output(BASE) if unit is None else unit) if is_unit else (
                'UnitPath=' + PATHS + '\n' if manager is None else manager)
            return subprocess.CompletedProcess(command, 0, stdout=text, stderr='')
        with patch.object(metadata.subprocess, 'run', side_effect=run):
            report = metadata.collect()
        self.assertEqual(len(calls), 2)
        self.assertFalse(report['migration_ready'])
        return report

    def test_observations(self):
        for inactive in (False, True):
            with self.subTest(inactive=inactive):
                unit = dict(BASE)
                if inactive:
                    unit.update(UnitFileState='disabled', ActiveState='inactive', SubState='dead')
                report = self.collect(output(unit))
                self.assertTrue(report['metadata_collected'])
                self.assertEqual(report['reasons'], [])
                self.assertEqual(report['unit'], unit)
                self.assertEqual(report['search_paths'], PATHS.split())

    def test_review_findings(self):
        cases = [dict(Names=metadata.UNIT + ' alias.service'), dict(Id='alias.service'),
                 dict(LoadState='not-found'), dict(UnitFileState='masked', FragmentPath='/dev/null'),
                 dict(UnitFileState='static'), dict(FragmentPath=''),
                 dict(SourcePath='/generated/source'), dict(DropInPaths='/override.conf'),
                 dict(NeedDaemonReload='yes'), dict(ActiveState='failed', SubState='failed'),
                 dict(ExecStart='')]
        for change in cases:
            with self.subTest(change=change):
                report = self.collect(output(dict(BASE, **change)))
                self.assertTrue(report['metadata_collected'])
                self.assertTrue(report['reasons'])
                self.assertEqual(report['unit'], dict(BASE, **change))

    def test_bad_serializations(self):
        for raw in ('', 'Id=x\n', output(BASE) + 'Id=duplicate\n',
                    output(BASE) + 'Extra=value\n', 'not-a-property\n'):
            with self.subTest(raw=raw):
                self.assertFalse(self.collect(raw)['metadata_collected'])
        for raw in ('', 'UnitPath=\n', 'UnitPath=relative\n',
                    'UnitPath=/path\\x20space\n', 'UnitPath="/path space"\n',
                    'UnitPath=/one  /two\n'):
            with self.subTest(raw=raw):
                report = self.collect(manager=raw)
                self.assertTrue(report['reasons'])
                self.assertEqual(report['search_paths'], [])

    def test_query_failures(self):
        for is_unit in (True, False):
            for error in (FileNotFoundError(), subprocess.TimeoutExpired('systemctl', 5),
                          subprocess.CalledProcessError(1, 'systemctl', output='PRIVATE')):
                with self.subTest(is_unit=is_unit, error=error):
                    report = self.collect(failure=(is_unit, error))
                    self.assertFalse(report['metadata_collected'])
                    self.assertTrue(report['reasons'])
                    self.assertNotIn('PRIVATE', str(report))


if __name__ == '__main__':
    unittest.main()
