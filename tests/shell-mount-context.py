#!/usr/bin/env python3
"""Synthetic supplementary context, correlated with retained guest evidence."""
import copy
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
VM = ROOT / 'tests/fixtures/shell-effective/systemd-261'
MODEL = runpy.run_path(str(TOOLS / 'shell-mount-context.py'))
GUEST = json.loads((VM / 'capture.json').read_text())
HOME = '/home/test'
SOURCE = HOME + '/.config/systemd/user'
UNIT = 'omarchy-shell.service'


def typed(value):
    return {'type': 'b' if type(value) is bool else 'as' if isinstance(value, list) else 's', 'data': value}


def record():
    # These extra typed observations are synthetic, NOT part of the VM capture.
    def identity(name, fragment='', source=''):
        return dict(Id=name, LoadState='loaded', FragmentPath=fragment, SourcePath=source,
                    DropInPaths=[], NeedDaemonReload=False, Transient=False)
    values = {
        'ShellUnit': dict(identity(UNIT, SOURCE + '/' + UNIT),
            After=['app.slice', 'basic.target', 'home.mount', 'graphical-session.target', '-.mount'],
            RequiresMountsFor=[], WantsMountsFor=[HOME]),
        'ShellService': dict(WorkingDirectory='!' + HOME, RootDirectory='', RootImage=''),
        'HomeUnit': identity('home.mount', source='/proc/self/mountinfo'),
        'HomeMount': dict(Where='/home'),
        'RootUnit': identity('-.mount'), 'RootMount': dict(Where='/'),
    }
    return dict(schema=1, collected=True, errors=[],
                properties={g: {k: typed(v) for k, v in props.items()} for g, props in values.items()})


def contents(root):
    return {str(p.relative_to(root)): ('link', os.readlink(p)) if p.is_symlink()
            else (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_symlink() or p.is_file()}


class MountContextTests(unittest.TestCase):
    def assess(self, value, effective=None, home=HOME):
        return MODEL['assess'](value, GUEST['effective'] if effective is None else effective,
                               GUEST['report']['unit'], home)

    def test_diagnostic_agreement(self):
        self.assertEqual(self.assess(record()), [])
        value = record()
        value['properties']['ShellUnit']['After']['data'].reverse()
        self.assertEqual(self.assess(value), [])
        # Correlate only the fields actually observed by the prior text diagnostic.
        diagnostic = (VM / 'dependency-origin.txt').read_text()
        for line in ('WorkingDirectory=!/home/test', 'WantsMountsFor=/home/test',
                     'RequiresMountsFor=', 'RootDirectory=', 'SourcePath=/proc/self/mountinfo'):
            self.assertIn(line + '\n', diagnostic)

    def test_each_field(self):
        for group, fields in record()['properties'].items():
            for name in fields:
                for case in ('missing', 'type', 'data', 'changed'):
                    with self.subTest(group=group, name=name, case=case):
                        value = record()
                        target = value['properties'][group]
                        if case == 'missing': del target[name]
                        elif case == 'type': target[name]['type'] = 'v'
                        elif case == 'data': target[name]['data'] = None
                        else:
                            old = target[name]['data']
                            target[name]['data'] = not old if type(old) is bool else (
                                old + ['other.mount'] if isinstance(old, list) else old + ' changed')
                        self.assertTrue(self.assess(value))

    def test_refusals(self):
        changes = [('ShellService', 'WorkingDirectory', HOME),
                   ('ShellService', 'WorkingDirectory', '!/home/other'),
                   ('ShellService', 'RootDirectory', '/rootfs'),
                   ('ShellService', 'RootImage', '/root.img'),
                   ('ShellUnit', 'RequiresMountsFor', [HOME]),
                   ('ShellUnit', 'WantsMountsFor', [HOME, HOME]),
                   ('ShellUnit', 'After', ['app.slice', 'basic.target', 'graphical-session.target', 'home.mount', 'other.mount']),
                   ('HomeUnit', 'FragmentPath', '/etc/systemd/user/home.mount'),
                   ('RootUnit', 'DropInPaths', ['/override.conf']),
                   ('HomeUnit', 'NeedDaemonReload', True),
                   ('ShellUnit', 'DropInPaths', ['/shell-override.conf']),
                   ('RootMount', 'Where', '/home'),
                   ('HomeMount', 'Where', '/home/test')]
        for group, key, data in changes:
            with self.subTest(group=group, key=key, data=data):
                value = record();value['properties'][group][key]['data'] = data
                self.assertTrue(self.assess(value))
        for home in (None, '', '/root', '/home/test/', '/home/../test', '/home/test/sub', '/home/a b', '/home/%u'):
            with self.subTest(home=home): self.assertTrue(self.assess(record(), home=home))
        for value in (None, {}, dict(record(), schema=True), dict(record(), collected=False),
                      dict(record(), errors=['query failed'])):
            self.assertTrue(self.assess(value))
        altered = copy.deepcopy(GUEST['effective'])
        altered['properties']['Service']['Restart']['data'] = 'always'
        self.assertTrue(self.assess(record(), effective=altered))

    def test_query_protocol(self):
        for group, (obj, interface, fields) in MODEL['GROUPS'].items():
            values = record()['properties'][group]
            good = '\n'.join(json.dumps(values[k]) for k in fields)
            for case in ('valid', 'missing', 'extra', 'duplicate', 'malformed', 'wrong-type', 'timeout', 'denied'):
                with self.subTest(group=group, case=case):
                    def run(command, **kwargs):
                        self.assertEqual(command, ['busctl', '--user', '--json=short', '--no-pager',
                            'get-property', 'org.freedesktop.systemd1', MODEL['PREFIX'] + obj,
                            'org.freedesktop.systemd1.' + interface, *fields])
                        self.assertEqual(kwargs['timeout'], 5)
                        self.assertTrue(kwargs['check'])
                        self.assertNotIn('shell', kwargs)
                        if case == 'timeout': raise subprocess.TimeoutExpired(command, 5)
                        if case == 'denied': raise subprocess.CalledProcessError(1, command)
                        raw = good
                        if case == 'missing': raw = '\n'.join(good.splitlines()[1:])
                        elif case == 'extra': raw += '\n{}'
                        elif case == 'duplicate': raw = raw.replace('"type":', '"type":"v","type":', 1)
                        elif case == 'malformed': raw = 'bad'
                        elif case == 'wrong-type': raw = raw.replace('"type":', '"bad":', 1)
                        return subprocess.CompletedProcess(command, 0, stdout=raw, stderr='')
                    with patch.object(subprocess, 'run', side_effect=run):
                        if case == 'valid': self.assertEqual(MODEL['query'](group), values)
                        else:
                            with self.assertRaises((ValueError, subprocess.SubprocessError)):
                                MODEL['query'](group)
        for group in MODEL['GROUPS']:
            def query(name):
                if name == group: raise ValueError('missing data')
                return record()['properties'][name]
            result = MODEL['collect'](query)
            self.assertFalse(result['collected'])
            self.assertEqual(len(result['errors']), 1)

    def test_inventory_cli(self):
        for case in ('consistent-context', 'no-context', 'no-home', 'wrong-home', 'dropin',
                     'no-hash', 'stale', 'changed-restart', 'changed-after', 'snapshot-change'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);units=root/'snapshot/units'
                (units/'graphical-session.target.wants').mkdir(parents=True)
                (root/'snapshot/autostart').mkdir()
                (units/UNIT).write_bytes((VM/UNIT).read_bytes())
                (units/'graphical-session.target.wants'/UNIT).symlink_to('../'+UNIT)
                capture=copy.deepcopy(GUEST);capture['mount_context']=record()
                props=capture['mount_context']['properties']
                if case=='no-context': del capture['mount_context']
                elif case=='dropin': props['HomeUnit']['DropInPaths']['data']=['/extra.conf']
                elif case=='no-hash': del capture['fragment']
                elif case=='stale': props['ShellUnit']['NeedDaemonReload']['data']=True
                elif case=='changed-restart': capture['effective']['properties']['Service']['Restart']['data']='always'
                elif case=='changed-after': capture['effective']['properties']['Unit']['After']['data'].append('other.mount')
                elif case=='snapshot-change': (units/UNIT).write_bytes(b'# edited\n'+(VM/UNIT).read_bytes())
                evidence=root/'capture.json';evidence.write_text(json.dumps(capture))
                before=contents(root)
                args=[sys.executable,str(TOOLS/'shell-ownership-inventory.py'),str(root/'snapshot'),
                      '--capture',str(evidence),'--source-unit-directory',SOURCE,'--require-effective']
                if case!='no-home': args+=['--mount-home','/home/other' if case=='wrong-home' else HOME]
                result=subprocess.run(args,capture_output=True,text=True,timeout=5,
                    env=dict(os.environ,PATH='',PYTHONDONTWRITEBYTECODE='1'))
                report=json.loads(result.stdout)
                self.assertEqual(result.returncode,1,result.stderr)
                self.assertEqual(report['mount_context_consistent'],case=='consistent-context')
                self.assertFalse(report['effective_properties_match'])
                self.assertFalse(report['consistent_observations'])
                self.assertFalse(report['migration_ready'])
                self.assertIn('Effective property differs from retained-vm-v1: After',report['reasons'])
                self.assertEqual(contents(root),before)

    def test_capture_cli(self):
        for case in ('valid', 'mount-failure', 'prerequisite-failure'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);fragment=root/UNIT;fragment.write_bytes((VM/UNIT).read_bytes())
                base=copy.deepcopy(GUEST)
                base['report']['unit']['FragmentPath']=str(fragment)
                fixture={'capture':base,'mount':record()}
                data=root/'input.json';data.write_text(json.dumps(fixture))
                script='#!'+sys.executable+'''
import json,os,pathlib,sys
fixture=json.loads(pathlib.Path(os.environ['FIXTURE']).read_text())
args=sys.argv[1:]
with open(os.environ['AUDIT'],'a') as f:f.write(json.dumps([pathlib.Path(sys.argv[0]).name,args])+'\\n')
if pathlib.Path(sys.argv[0]).name=='systemctl':
 assert args[:4]==['--user','--no-pager','show','--all']
 if os.environ['CASE']=='prerequisite-failure':sys.exit(1)
 values=fixture['capture']['report']['unit' if len(args)==6 else 'manager']
 for k,v in values.items():print(k+'='+v)
else:
 assert args[:4]==['--user','--json=short','--no-pager','get-property']
 assert args[4]=='org.freedesktop.systemd1'
 obj,interface=args[5].split('/')[-1],args[6].split('.')[-1]
 fields=args[7:]
 if obj=='omarchy_2dshell_2eservice' and len(fields)>10:
  values=fixture['capture']['effective']['properties'][interface]
 else:
  if os.environ['CASE']=='mount-failure':sys.exit(1)
  group={('omarchy_2dshell_2eservice','Unit'):'ShellUnit',('omarchy_2dshell_2eservice','Service'):'ShellService',('home_2emount','Unit'):'HomeUnit',('home_2emount','Mount'):'HomeMount',('_2d_2emount','Unit'):'RootUnit',('_2d_2emount','Mount'):'RootMount'}[(obj,interface)]
  values=fixture['mount']['properties'][group]
 for k in fields:print(json.dumps(values[k]))
'''
                for name in ('systemctl','busctl'):
                    (root/name).write_text(script);(root/name).chmod(0o700)
                output=root/'output.json'
                result=subprocess.run([sys.executable,str(TOOLS/'capture-shell-ownership-metadata.py'),
                    str(output),'--effective-properties','--hash-fragment','--mount-context'],
                    capture_output=True,text=True,timeout=20,env=dict(os.environ,PATH=str(root),
                    PYTHONDONTWRITEBYTECODE='1',CASE=case,FIXTURE=str(data),AUDIT=str(root/'audit')))
                evidence=json.loads(output.read_text())
                self.assertEqual(result.returncode,0 if case=='valid' else 1,result.stderr)
                self.assertEqual(evidence['mount_context']['collected'],case=='valid')
                self.assertEqual(evidence['capture_exit_status'],result.returncode)
                self.assertEqual(output.stat().st_mode&0o777,0o600)
                self.assertFalse(evidence['report']['migration_ready'])
                calls=(root/'audit').read_text().splitlines()
                self.assertEqual(len(calls),4 if case=='prerequisite-failure' else 10)
                self.assertEqual(json.loads(data.read_text()),fixture)

    def test_option_pairing(self):
        for tool,args in [('capture-shell-ownership-metadata.py',['/absent','--mount-context']),
                          ('shell-ownership-inventory.py',['/absent','--mount-home',HOME])]:
            result=subprocess.run([sys.executable,str(TOOLS/tool),*args],capture_output=True,text=True)
            self.assertEqual(result.returncode,2)


if __name__=='__main__':
    unittest.main()
