#!/usr/bin/env python3
"""Synthetic changing-query fixtures; never contact the host user manager."""
import copy
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / 'tools'
FIXTURE = ROOT / 'tests/fixtures/shell-mount/systemd-261'
GUEST = json.loads((FIXTURE / 'capture.json').read_text())
MODEL = runpy.run_path(str(TOOLS / 'shell-capture-coherence.py'))
UNIT = 'omarchy-shell.service'

FAKE = '''
import json, os, pathlib, sys
args = sys.argv[1:]
audit = pathlib.Path(os.environ['AUDIT'])
calls = audit.read_text().splitlines() if audit.exists() else []
index = len(calls)
with audit.open('a') as stream:
 stream.write(json.dumps([pathlib.Path(sys.argv[0]).name, args])+'\\n')
data = json.loads(pathlib.Path(os.environ['FIXTURE']).read_text())
case = os.environ['CASE']
second = index >= 10
if case == 'initial-failure' and index == 0: sys.exit(1)
if case == 'final-query-failure' and index == 18: sys.exit(1)
if case == 'fragment-change' and index == 10:
 pathlib.Path(os.environ['FRAGMENT']).write_text('# changed during capture\\n')
if pathlib.Path(sys.argv[0]).name == 'systemctl':
 assert args[:4] == ['--user','--no-pager','show','--all']
 assert len(args) in (5,6)
 assert len(args) == 5 or args[5] == 'omarchy-shell.service'
 values = data['report']['unit' if len(args)==6 else 'manager']
 if second:
  changes = {'reload':('NeedDaemonReload','yes'), 'identity':('Id','other.service'),
   'fragment-path':('FragmentPath','/other.service'), 'dropin':('DropInPaths','/extra.conf'),
   'activation':('UnitFileState','disabled'), 'runtime':('ActiveState','inactive'),
   'launch':('ExecStart','different'), 'search-path':('UnitPath','/other')}
  if case in changes:
   key,value=changes[case]
   if key in values: values[key]=value
 for key,value in values.items(): print(key+'='+value)
else:
 assert args[:4] == ['--user','--json=short','--no-pager','get-property']
 assert args[4] == 'org.freedesktop.systemd1'
 obj, interface = args[5].split('/')[-1], args[6].split('.')[-1]
 fields = args[7:]
 if obj == 'omarchy_2dshell_2eservice' and len(fields)>10:
  values=data['effective']['properties'][interface]
  if second and case == 'effective-change' and interface == 'Service':
   values['Restart']['data']='always'
 else:
  group={('omarchy_2dshell_2eservice','Unit'):'ShellUnit',
   ('omarchy_2dshell_2eservice','Service'):'ShellService',
   ('home_2emount','Unit'):'HomeUnit',('home_2emount','Mount'):'HomeMount',
   ('_2d_2emount','Unit'):'RootUnit',('_2d_2emount','Mount'):'RootMount'}[(obj,interface)]
  values=data['mount_context']['properties'][group]
  if second and case == 'mount-change' and group == 'HomeMount': values['Where']['data']='/other'
  if second and case == 'malformed' and group == 'ShellUnit':
   print('not json'); sys.exit(0)
 for key in fields: print(json.dumps(values[key]))
'''


class CoherenceTests(unittest.TestCase):
    def test_capture_cli_changes_and_failures(self):
        cases = ('stable', 'reload', 'identity', 'fragment-path', 'dropin', 'activation',
                 'runtime', 'launch', 'search-path', 'fragment-change', 'effective-change',
                 'mount-change', 'initial-failure', 'final-query-failure', 'malformed')
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                fragment = root / UNIT
                fragment.write_bytes((FIXTURE / UNIT).read_bytes())
                data = copy.deepcopy(GUEST)
                data['report']['unit']['FragmentPath'] = str(fragment)
                fixture = root / 'input.json'
                fixture.write_text(json.dumps(data))
                for name in ('systemctl', 'busctl'):
                    command = root / name
                    command.write_text('#!' + sys.executable + '\n' + FAKE)
                    command.chmod(0o700)
                output = root / 'output.json'
                result = subprocess.run([sys.executable, str(TOOLS / 'capture-shell-ownership-metadata.py'),
                    str(output), '--hash-fragment', '--effective-properties', '--mount-context',
                    '--check-coherence'], capture_output=True, text=True, timeout=20,
                    env=dict(os.environ, PATH=str(root), PYTHONDONTWRITEBYTECODE='1',
                             CASE=case, FIXTURE=str(fixture), FRAGMENT=str(fragment), AUDIT=str(root/'audit')))
                self.assertEqual(result.returncode, 0 if case == 'stable' else 1, result.stderr)
                evidence = json.loads(output.read_text())
                self.assertEqual(evidence['capture_exit_status'], result.returncode)
                self.assertEqual(evidence['coherence']['agrees'], case == 'stable')
                self.assertEqual(bool(MODEL['assess'](evidence)), case != 'stable')
                self.assertFalse(evidence['report']['migration_ready'])
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                self.assertEqual(json.loads(fixture.read_text()), data)
                calls = [json.loads(line) for line in (root/'audit').read_text().splitlines()]
                self.assertEqual(len(calls), 4 if case == 'initial-failure' else 20)
                if case != 'initial-failure':
                    self.assertEqual([name for name, args in calls],
                                     ['systemctl']*2 + ['busctl']*16 + ['systemctl']*2)
                if case == 'fragment-change':
                    self.assertIn('Observation changed: fragment', evidence['coherence']['errors'])
                elif case not in ('stable', 'initial-failure'):
                    self.assertTrue(any('Observation changed:' in error for error in evidence['coherence']['errors']))

    def test_comparison_reassesses_and_preserves_refusal(self):
        for case in ('stable', 'missing', 'changed', 'forged-agreement', 'boolean-schema',
                     'extra', 'failed-status', 'incomplete', 'wrong-type', 'array-order',
                     'automatic-stable', 'automatic-changed'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp); snap = root/'snapshot'; units = snap/'units'
                (units/'graphical-session.target.wants').mkdir(parents=True)
                (snap/'autostart').mkdir()
                (units/UNIT).write_bytes((FIXTURE/UNIT).read_bytes())
                (units/'graphical-session.target.wants'/UNIT).symlink_to('../'+UNIT)
                evidence = copy.deepcopy(GUEST)
                before = MODEL['observations'](evidence)
                after = copy.deepcopy(before)
                if case in ('changed', 'forged-agreement', 'automatic-changed'):
                    after['effective']['properties']['Service']['Restart']['data']='always'
                if case == 'incomplete': del after['report']
                if case == 'wrong-type': after['mount_context']['properties']['ShellUnit']['Transient']['data']=0
                if case == 'array-order': after['effective']['properties']['Unit']['After']['data'].reverse()
                evidence['coherence'] = MODEL['record'](before, after)
                if case == 'missing': del evidence['coherence']
                if case == 'forged-agreement': evidence['coherence'].update(agrees=True, errors=[])
                if case == 'boolean-schema': evidence['coherence']['schema']=True
                if case == 'extra': evidence['coherence']['extra']=None
                if case == 'failed-status': evidence['capture_exit_status']=1
                path = root/'capture.json'; path.write_text(json.dumps(evidence))
                result = subprocess.run([sys.executable,str(TOOLS/'shell-ownership-inventory.py'),str(snap),
                    '--capture',str(path),'--source-unit-directory','/home/test/.config/systemd/user',
                    '--require-effective','--mount-home','/home/test'] +
                    ([] if case.startswith('automatic-') else ['--require-coherence']),
                    capture_output=True,text=True,timeout=5,env=dict(os.environ,PATH='',PYTHONDONTWRITEBYTECODE='1'))
                self.assertEqual(result.returncode,1,result.stderr)
                report=json.loads(result.stdout)
                self.assertEqual(report['capture_coherence_agrees'],case in ('stable', 'automatic-stable'))
                self.assertFalse(report['migration_ready'])
                self.assertFalse(report['consistent_observations'])
                self.assertFalse(report['effective_properties_match'])
                self.assertEqual(report['mount_context_consistent'],case in ('stable', 'automatic-stable'))
                self.assertIn('Effective property differs from retained-vm-v1: After',report['reasons'])
                self.assertEqual(json.loads(path.read_text()),evidence)

    def test_missing_evidence_and_option_dependencies(self):
        for key in MODEL['FIELDS']:
            before=MODEL['observations'](GUEST); after=copy.deepcopy(before)
            del after[key]
            self.assertFalse(MODEL['record'](before,after)['agrees'])
        for tool,args in [('capture-shell-ownership-metadata.py',['/absent','--check-coherence']),
                          ('shell-ownership-inventory.py',['/absent','--require-coherence'])]:
            result=subprocess.run([sys.executable,str(TOOLS/tool),*args],capture_output=True,text=True,
                                  env=dict(os.environ,PATH='',PYTHONDONTWRITEBYTECODE='1'))
            self.assertEqual(result.returncode,2)


if __name__ == '__main__':
    unittest.main()
