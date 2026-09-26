#!/usr/bin/env python3
"""Supplementary mount-context observations; never relaxes ownership recognition."""
import json
import os
from pathlib import Path
import re
import runpy
import subprocess

EFFECTIVE = runpy.run_path(str(Path(__file__).with_name('shell-effective-properties.py')))
PREFIX = '/org/freedesktop/systemd1/unit/'
IDENTITY = {'Id': 's', 'LoadState': 's', 'FragmentPath': 's', 'SourcePath': 's',
            'DropInPaths': 'as', 'NeedDaemonReload': 'b', 'Transient': 'b'}
# Fixed objects only: no paths/units discovered in evidence are queried.
GROUPS = {
    'ShellUnit': ('omarchy_2dshell_2eservice', 'Unit',
                  dict(IDENTITY, After='as', RequiresMountsFor='as', WantsMountsFor='as')),
    'ShellService': ('omarchy_2dshell_2eservice', 'Service',
                     dict(WorkingDirectory='s', RootDirectory='s', RootImage='s')),
    'HomeUnit': ('home_2emount', 'Unit', IDENTITY),
    'HomeMount': ('home_2emount', 'Mount', dict(Where='s')),
    'RootUnit': ('_2d_2emount', 'Unit', IDENTITY),
    'RootMount': ('_2d_2emount', 'Mount', dict(Where='s')),
}


def validate(group, values):
    fields = GROUPS[group][2]
    if not isinstance(values, dict) or set(values) != set(fields):
        raise ValueError('Missing or extra mount-context properties: ' + group)
    for name, signature in fields.items():
        prop = values[name]
        if (not isinstance(prop, dict) or set(prop) != {'type', 'data'} or prop['type'] != signature):
            raise ValueError('Invalid mount-context signature: ' + name)
        value = prop['data']
        valid = (type(value) is str if signature == 's' else
                 type(value) is bool if signature == 'b' else
                 isinstance(value, list) and all(type(x) is str for x in value))
        if not valid:
            raise ValueError('Invalid mount-context data: ' + name)


def query(group):
    obj, interface, fields = GROUPS[group]
    result = subprocess.run(
        ['busctl', '--user', '--json=short', '--no-pager', 'get-property',
         EFFECTIVE['DESTINATION'], PREFIX + obj, EFFECTIVE['DESTINATION'] + '.' + interface, *fields],
        capture_output=True, text=True, timeout=5, check=True,
        env=dict(os.environ, LC_ALL='C', SYSTEMD_COLORS='0'))
    rows = result.stdout.splitlines()
    if len(rows) != len(fields):
        raise ValueError('Missing or extra mount-context replies')
    values = dict(zip(fields, (json.loads(row, object_pairs_hook=EFFECTIVE['unique_fields']) for row in rows)))
    validate(group, values)
    return values


def collect(query_fn=query):
    record = {'schema': 1, 'collected': False, 'properties': {}, 'errors': []}
    for group in GROUPS:
        try:
            values = query_fn(group)
            validate(group, values)
            record['properties'][group] = values
        except (OSError, UnicodeError, ValueError, subprocess.SubprocessError) as error:
            record['errors'].append(group + ' query failed: ' + type(error).__name__)
    record['collected'] = len(record['properties']) == len(GROUPS) and not record['errors']
    return record


def assess(record, effective, metadata, home):
    """Diagnostic agreement only; origins cannot be proven by these observations."""
    if not isinstance(home, str) or not re.fullmatch(r'/home/[A-Za-z0-9_][A-Za-z0-9_-]{0,63}', home):
        return ['Explicit supported --mount-home is required']
    if (not isinstance(record, dict) or set(record) != {'schema', 'collected', 'properties', 'errors'} or
            type(record['schema']) is not int or record['schema'] != 1 or
            record['collected'] is not True or record['errors'] != [] or
            not isinstance(record['properties'], dict) or set(record['properties']) != set(GROUPS)):
        return ['Mount-context evidence is missing, incomplete or malformed']
    try:
        for group in GROUPS:
            validate(group, record['properties'][group])
    except ValueError as error:
        return [str(error)]
    # Keep the existing assessment intact. Only its known After disagreement is
    # compatible with this supplementary explanation, never with an overall pass.
    differences = EFFECTIVE['assess'](effective, metadata)
    if differences != ['Effective property differs from retained-vm-v1: After']:
        return ['Mount context requires otherwise consistent effective evidence with the known After refusal']
    expected_path = home + '/.config/systemd/user/omarchy-shell.service'
    expected_after = ['app.slice', 'basic.target', 'graphical-session.target', 'home.mount', '-.mount']
    props = record['properties']
    reasons = []
    def check(group, name, expected):
        value = props[group][name]['data']
        matches = (len(value) == len(expected) and set(value) == set(expected)
                   if isinstance(expected, list) else value == expected)
        if not matches:
            reasons.append('Mount-context disagreement: ' + group + '.' + name)
    for group, name, source in [('ShellUnit', 'omarchy-shell.service', ''),
                                ('HomeUnit', 'home.mount', '/proc/self/mountinfo'),
                                ('RootUnit', '-.mount', '')]:
        for key, value in dict(Id=name, LoadState='loaded',
                FragmentPath=expected_path if group == 'ShellUnit' else '',
                SourcePath=source, DropInPaths=[], NeedDaemonReload=False, Transient=False).items():
            check(group, key, value)
    for key in ('Id', 'FragmentPath', 'SourcePath', 'DropInPaths', 'NeedDaemonReload', 'Transient', 'After'):
        check('ShellUnit', key, effective['properties']['Unit'][key]['data'])
    if metadata['FragmentPath'] != expected_path:
        reasons.append('Mount-context home disagrees with mapped fragment directory')
    check('ShellUnit', 'After', expected_after)
    check('ShellUnit', 'RequiresMountsFor', [])
    check('ShellUnit', 'WantsMountsFor', [home])
    check('ShellService', 'WorkingDirectory', '!' + home)
    check('ShellService', 'RootDirectory', '')
    check('ShellService', 'RootImage', '')
    check('HomeMount', 'Where', '/home')
    check('RootMount', 'Where', '/')
    return reasons
