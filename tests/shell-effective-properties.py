#!/usr/bin/env python3
"""Typed property/refusal and end-to-end tests; no real manager access."""
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
TOOLS = ROOT / 'tools'
MODEL = runpy.run_path(str(TOOLS / 'shell-effective-properties.py'))
VM = ROOT / 'tests/fixtures/shell-metadata/fragment-261'
SYNTHETIC = json.loads((ROOT / 'tests/fixtures/shell-effective/synthetic.json').read_text())
CAPTURE = json.loads((VM / 'capture.json').read_text())
SOURCE = '/home/test/.config/systemd/user'
UNIT = 'omarchy-shell.service'


def snapshot(root):
    return {str(p.relative_to(root)): ('link', os.readlink(p)) if p.is_symlink()
            else (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_symlink() or p.is_file()}


class EffectiveTests(unittest.TestCase):
    def compare(self, evidence, text=None, require=True, link=True, dropin=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snap = root / 'snapshot'
            units = snap / 'units'
            units.mkdir(parents=True)
            (snap / 'autostart').mkdir()
            (units / UNIT).write_bytes((VM / UNIT).read_bytes() if text is None else text)
            if link:
                wants = units / 'graphical-session.target.wants'
                wants.mkdir()
                (wants / UNIT).symlink_to('../' + UNIT)
            if dropin:
                (units / (UNIT + '.d')).mkdir()
                (units / (UNIT + '.d') / 'override.conf').write_text('[Service]\nRestart=always\n')
            path = root / 'capture.json'
            path.write_text(json.dumps(evidence))
            before = snapshot(root)
            command = [sys.executable, str(TOOLS / 'shell-ownership-inventory.py'), str(snap),
                       '--capture', str(path), '--source-unit-directory', SOURCE]
            result = subprocess.run(command + (['--require-effective'] if require else []),
                                    env=dict(os.environ, PATH='', PYTHONDONTWRITEBYTECODE='1'),
                                    capture_output=True, text=True, cwd=root, timeout=5)
            self.assertEqual(snapshot(root), before)
            report = json.loads(result.stdout)
            self.assertFalse(report['migration_ready'])
            self.assertEqual(result.returncode, 0 if report['consistent_observations'] else 1)
            return report

    def evidence(self):
        return dict(copy.deepcopy(CAPTURE), effective=copy.deepcopy(SYNTHETIC))

    def test_acceptance(self):
        for case in ('exact', 'reordered', 'condition-untested', 'condition-failed', 'inactive-disabled'):
            with self.subTest(case=case):
                evidence = self.evidence()
                props = evidence['effective']['properties']
                if case == 'reordered':
                    for group in props.values():
                        for prop in group.values():
                            if prop['type'] == 'as':
                                prop['data'].reverse()
                if case.startswith('condition-'):
                    props['Unit']['Conditions']['data'][0][4] = 0 if case.endswith('untested') else -1
                if case == 'inactive-disabled':
                    evidence['report']['unit'].update(ActiveState='inactive', SubState='dead', UnitFileState='disabled')
                report = self.compare(evidence, link=case != 'inactive-disabled')
                self.assertTrue(report['effective_properties_match'], report['reasons'])
                self.assertTrue(report['fragment_bytes_match'])

    def test_every_property_missing_changed_or_mistyped(self):
        for group, fields in SYNTHETIC['properties'].items():
            for name, prop in fields.items():
                for change in ('missing', 'changed', 'wrong-type', 'wrong-data'):
                    with self.subTest(group=group, name=name, change=change):
                        evidence = self.evidence()
                        target = evidence['effective']['properties'][group]
                        if change == 'missing':
                            del target[name]
                        elif change == 'wrong-type':
                            target[name]['type'] = 'v'
                        elif change == 'wrong-data':
                            target[name]['data'] = None
                        else:
                            value = prop['data']
                            target[name]['data'] = (not value if type(value) is bool else
                                                    value + 1 if type(value) is int else
                                                    value + ' changed' if type(value) is str else
                                                    value + ['unexpected'])
                        report = self.compare(evidence)
                        self.assertFalse(report['effective_properties_match'])
                        self.assertTrue(report['reasons'])

    def test_adversarial_cases(self):
        cases = ('legacy', 'no-hash', 'wrong-bytes', 'dropin', 'stale', 'override-source',
                 'snapshot-dropin', 'unknown-shape', 'failed-capture', 'incomplete',
                 'extra-interface', 'extra-property', 'bool-integer', 'condition-bool',
                 'env-duplicate', 'env-quoted', 'env-file', 'optional-env-file', 'exec-flags',
                 'exec-wrapper', 'extra-exec', 'exec-bool-pid', 'execution-hook', 'alias')
        for case in cases:
            with self.subTest(case=case):
                evidence = self.evidence()
                props = evidence['effective']['properties']
                unit, service = props['Unit'], props['Service']
                text = None
                if case == 'legacy': del evidence['effective']
                elif case == 'no-hash': del evidence['fragment']
                elif case == 'wrong-bytes': text = b'# changed\n' + (VM / UNIT).read_bytes()
                elif case == 'dropin': unit['DropInPaths']['data'] = ['/override.conf']
                elif case == 'stale': unit['NeedDaemonReload']['data'] = True
                elif case == 'override-source': unit['FragmentPath']['data'] = '/other/service'
                elif case == 'unknown-shape': text = b'[Service]\nExecStart=/usr/bin/quickshell -n -p /usr/share/omarchy/shell\n'
                elif case == 'failed-capture': evidence['capture_exit_status'] = 1
                elif case == 'incomplete': evidence['effective']['collected'] = False
                elif case == 'extra-interface': props['Extra'] = {}
                elif case == 'extra-property': unit['Extra'] = {'type': 's', 'data': ''}
                elif case == 'bool-integer': unit['StartLimitBurst']['data'] = True
                elif case == 'condition-bool': unit['Conditions']['data'][0][1] = 0
                elif case == 'env-duplicate': service['Environment']['data'] = ['QS_DISABLE_FILE_WATCHER=1'] * 2
                elif case == 'env-quoted': service['Environment']['data'][0] = '"QS_DISABLE_FILE_WATCHER=1"'
                elif case in ('env-file', 'optional-env-file'):
                    service['EnvironmentFiles']['data'] = [['/never/read', case == 'optional-env-file']]
                elif case == 'exec-flags': service['ExecStartEx']['data'][0][2] = ['ignore-failure']
                elif case == 'exec-wrapper': service['ExecStartEx']['data'][0][:2] = ['/bin/sh', ['/bin/sh', '-c', 'touch SHOULD_NOT_EXIST']]
                elif case == 'extra-exec': service['ExecStartEx']['data'] *= 2
                elif case == 'exec-bool-pid': service['ExecStartEx']['data'][0][7] = True
                elif case == 'execution-hook': service['ExecStartPre']['data'] = [['/bin/false']]
                elif case == 'alias': unit['Id']['data'] = 'other.service'
                if case == 'unknown-shape':
                    evidence['fragment']['sha256'] = hashlib.sha256(text).hexdigest()
                    evidence['fragment']['size_bytes'] = len(text)
                report = self.compare(evidence, text=text, dropin=case == 'snapshot-dropin')
                self.assertFalse(report['effective_properties_match'], case)
        # Supplied effective evidence cannot be silently ignored without the flag.
        evidence = self.evidence()
        evidence['effective']['properties']['Service']['Restart']['data'] = 'always'
        self.assertFalse(self.compare(evidence, require=False)['consistent_observations'])
        self.assertTrue(self.compare(CAPTURE, require=False)['consistent_observations'])

    def test_query_protocol(self):
        for interface, fields in MODEL['FIELDS'].items():
            values = SYNTHETIC['properties'][interface]
            good = '\n'.join(json.dumps(values[name]) for name in fields) + '\n'
            for case in ('valid', 'missing', 'extra', 'duplicate-json', 'malformed', 'wrong-type', 'timeout', 'failure'):
                with self.subTest(interface=interface, case=case):
                    def run(command, **kwargs):
                        self.assertEqual(command, ['busctl', '--user', '--json=short', '--no-pager',
                            'get-property', MODEL['DESTINATION'], MODEL['OBJECT'],
                            MODEL['DESTINATION'] + '.' + interface, *fields])
                        self.assertEqual(kwargs['timeout'], 5)
                        self.assertTrue(kwargs['check'])
                        self.assertNotIn('shell', kwargs)
                        if case == 'timeout': raise subprocess.TimeoutExpired(command, 5)
                        if case == 'failure': raise subprocess.CalledProcessError(1, command)
                        raw = good
                        if case == 'missing': raw = '\n'.join(good.splitlines()[1:])
                        if case == 'extra': raw += '{}\n'
                        if case == 'duplicate-json': raw = raw.replace('"type":', '"type":"s", "type":', 1)
                        if case == 'malformed': raw = '{\n'
                        if case == 'wrong-type': raw = raw.replace('"type":', '"bogus":', 1)
                        return subprocess.CompletedProcess(command, 0, stdout=raw, stderr='')
                    with patch.object(subprocess, 'run', side_effect=run):
                        if case == 'valid':
                            self.assertEqual(MODEL['query'](interface, fields), values)
                        else:
                            with self.assertRaises((ValueError, subprocess.SubprocessError)):
                                MODEL['query'](interface, fields)

    def test_capture_cli(self):
        for case in ('valid', 'query-failure', 'missing', 'mistyped', 'hash-valid', 'hash-refused'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                properties = root / 'properties.json'
                expected_properties = copy.deepcopy(SYNTHETIC['properties'])
                unit = copy.deepcopy(CAPTURE['report']['unit'])
                if case.startswith('hash-'):
                    fragment = root / UNIT
                    fragment.write_bytes((VM / UNIT).read_bytes())
                    unit['FragmentPath'] = str(fragment)
                    expected_properties['Unit']['FragmentPath']['data'] = str(fragment)
                    if case == 'hash-refused': fragment.unlink()
                properties.write_text(json.dumps(expected_properties))
                script = '#!' + sys.executable + '''
import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['AUDIT'], 'a') as f: f.write(json.dumps([pathlib.Path(sys.argv[0]).name, args])+'\\n')
if pathlib.Path(sys.argv[0]).name == 'systemctl':
    assert args[:4] == ['--user', '--no-pager', 'show', '--all']
    values = json.loads(os.environ['UNIT']) if args[-1] == 'omarchy-shell.service' else {'UnitPath': '/home/test/.config/systemd/user'}
    for k,v in values.items(): print(k+'='+v)
else:
    assert args[:4] == ['--user', '--json=short', '--no-pager', 'get-property']
    assert args[4:6] == ['org.freedesktop.systemd1', '/org/freedesktop/systemd1/unit/omarchy_2dshell_2eservice']
    if os.environ['CASE'] == 'query-failure': sys.exit(1)
    group = args[6].split('.')[-1]
    values = json.loads(pathlib.Path(os.environ['PROPERTIES']).read_text())[group]
    for i,k in enumerate(args[7:]):
        if os.environ['CASE'] == 'missing' and i == 0: continue
        v = values[k]
        if os.environ['CASE'] == 'mistyped' and i == 0: v['type'] = 'v'
        print(json.dumps(v))
'''
                for name in ('systemctl', 'busctl'):
                    (root / name).write_text(script)
                    (root / name).chmod(0o700)
                output = root / 'capture.json'
                result = subprocess.run([sys.executable, str(TOOLS / 'capture-shell-ownership-metadata.py'),
                                         str(output), '--effective-properties'] +
                                        (['--hash-fragment'] if case.startswith('hash-') else []),
                    env=dict(os.environ, PATH=str(root), PYTHONDONTWRITEBYTECODE='1', CASE=case,
                             UNIT=json.dumps(unit), PROPERTIES=str(properties), AUDIT=str(root / 'audit')),
                    capture_output=True, text=True, timeout=20)
                evidence = json.loads(output.read_text())
                self.assertEqual(result.returncode, 0 if case in ('valid', 'hash-valid') else 1, result.stderr)
                self.assertEqual(evidence['effective']['collected'], case in ('valid', 'hash-valid', 'hash-refused'))
                self.assertEqual(evidence['collector_exit_status'], 0)
                self.assertEqual(evidence['capture_exit_status'], result.returncode)
                self.assertFalse(evidence['report']['migration_ready'])
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                self.assertEqual(len((root / 'audit').read_text().splitlines()), 4)
                self.assertEqual(json.loads(properties.read_text()), expected_properties)
                if case.startswith('hash-'):
                    self.assertEqual(evidence['fragment']['outcome'],
                                     'ok' if case == 'hash-valid' else 'refused')
                if case == 'valid': self.assertEqual(evidence['effective'], SYNTHETIC)

    def test_required_option(self):
        result = subprocess.run([sys.executable, str(TOOLS / 'shell-ownership-inventory.py'),
                                 '/absent', '--require-effective'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
