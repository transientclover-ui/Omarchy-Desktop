#!/usr/bin/env python3
"""Bounded typed property evidence for the retained VM unit; no lifecycle calls."""
import json
import os
import subprocess

DESTINATION = 'org.freedesktop.systemd1'
OBJECT = '/org/freedesktop/systemd1/unit/omarchy_2dshell_2eservice'
COMMAND = '/usr/bin/quickshell'
ARGV = [COMMAND, '-n', '-p', '/usr/share/omarchy/shell']
INFINITY = 2**64 - 1
EXEC = 'a(sasbttttuii)'
# Expected user-manager defaults are a bounded candidate contract, not captured
# VM observations. Unknown versions/defaults must refuse pending review.
UNIT_EXPECTED = {
    'DefaultDependencies': ('b', True), 'Transient': ('b', False),
    'After': ('as', ['app.slice', 'basic.target', 'graphical-session.target']),
    'Before': ('as', ['shutdown.target']),
    'Requires': ('as', ['app.slice', 'basic.target']),
    'PartOf': ('as', ['graphical-session.target']),
    'Conflicts': ('as', ['shutdown.target']),
    **{key: ('as', []) for key in ('Wants', 'Requisite', 'BindsTo', 'Upholds',
       'OnFailure', 'OnSuccess', 'PropagatesStopTo', 'StopPropagatedFrom', 'JoinsNamespaceOf',
       'PropagatesReloadTo', 'ReloadPropagatedFrom')},
    'Asserts': ('a(sbbsi)', []),
    'StartLimitIntervalUSec': ('t', 10_000_000),
    'StartLimitBurst': ('u', 5),
    'StartLimitAction': ('s', 'none'),
    'FailureAction': ('s', 'none'),
    'SuccessAction': ('s', 'none'),
}
SERVICE_EXPECTED = {
    'Type': ('s', 'simple'), 'ExitType': ('s', 'main'),
    'RemainAfterExit': ('b', False), 'PIDFile': ('s', ''), 'BusName': ('s', ''),
    'Slice': ('s', 'app.slice'),
    'Environment': ('as', ['QS_DISABLE_FILE_WATCHER=1', 'QS_NO_RELOAD_POPUP=1']),
    'EnvironmentFiles': ('a(sb)', []), 'PassEnvironment': ('as', []),
    'UnsetEnvironment': ('as', []),
    **{key: (EXEC, []) for key in ('ExecCondition', 'ExecStartPre', 'ExecStartPost',
                                    'ExecReload', 'ExecReloadPost', 'ExecStop', 'ExecStopPost')},
    'Restart': ('s', 'on-failure'), 'RestartMode': ('s', 'normal'),
    'RestartUSec': ('t', 3_000_000), 'RestartSteps': ('u', 0),
    'RestartMaxDelayUSec': ('t', INFINITY),
    **{key: ('(aiai)', [[], []]) for key in ('SuccessExitStatus',
                               'RestartPreventExitStatus', 'RestartForceExitStatus')},
    'TimeoutStartUSec': ('t', 90_000_000), 'TimeoutStopUSec': ('t', 90_000_000),
    'RuntimeMaxUSec': ('t', INFINITY), 'WatchdogUSec': ('t', 0),
    'KillMode': ('s', 'control-group'), 'KillSignal': ('i', 15),
    'RestartKillSignal': ('i', 15), 'FinalKillSignal': ('i', 9),
    'SendSIGKILL': ('b', True),
}
IDENTITY = {'Id': 's', 'FragmentPath': 's', 'SourcePath': 's',
            'DropInPaths': 'as', 'NeedDaemonReload': 'b'}
FIELDS = {
    'Unit': {**IDENTITY, **{k: v[0] for k, v in UNIT_EXPECTED.items()},
             'Conditions': 'a(sbbsi)'},
    'Service': {**{k: v[0] for k, v in SERVICE_EXPECTED.items()},
                'ExecStartEx': 'a(sasasttttuii)'},
}


def unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON field')
        result[key] = value
    return result


def query(interface, fields):
    # Explicit object and allowlisted Properties.Get reads only. Never LoadUnit,
    # GetAll, start/stop/reload, environment-file reads or arbitrary commands.
    result = subprocess.run(
        ['busctl', '--user', '--json=short', '--no-pager',
         'get-property', DESTINATION, OBJECT, DESTINATION + '.' + interface, *fields],
        capture_output=True, text=True, timeout=5, check=True,
        env=dict(os.environ, LC_ALL='C', SYSTEMD_COLORS='0'))
    rows = result.stdout.splitlines()
    if len(rows) != len(fields):
        raise ValueError('Missing or extra property replies')
    values = dict(zip(fields, (json.loads(row, object_pairs_hook=unique_fields) for row in rows)))
    validate_group(interface, values)
    return values


def validate_group(interface, values):
    if not isinstance(values, dict) or set(values) != set(FIELDS[interface]):
        raise ValueError('Missing or extra effective properties: ' + interface)
    for name, signature in FIELDS[interface].items():
        prop = values[name]
        if (not isinstance(prop, dict) or set(prop) != {'type', 'data'} or
                prop['type'] != signature):
            raise ValueError('Invalid typed property: ' + name)
        data = prop['data']
        if signature in ('s', 'b'):
            valid = type(data) is (str if signature == 's' else bool)
        elif signature in ('t', 'u', 'i'):
            low, high = (-(2**31), 2**31-1) if signature == 'i' else (
                0, 2**64-1 if signature == 't' else 2**32-1)
            valid = type(data) is int and low <= data <= high
        elif signature == 'as':
            valid = isinstance(data, list) and all(type(x) is str for x in data)
        else:
            # Structured arrays have a deliberately narrow assessment below:
            # empty only, or one exact condition/command with typed runtime fields.
            valid = isinstance(data, list)
        if not valid:
            raise ValueError('Invalid property data: ' + name)


def collect(query_fn=query):
    record = {'schema': 1, 'collected': False, 'properties': {}, 'errors': []}
    for interface, fields in FIELDS.items():
        try:
            values = query_fn(interface, fields)
            validate_group(interface, values)
            record['properties'][interface] = values
        except (OSError, UnicodeError, ValueError, subprocess.SubprocessError) as error:
            record['errors'].append(interface + ' query failed: ' + type(error).__name__)
    record['collected'] = len(record['properties']) == len(FIELDS) and not record['errors']
    return record


def assess(record, metadata):
    """Return refusal reasons; no evidence field is trusted as an approval."""
    reasons = []
    if (not isinstance(record, dict) or set(record) != {'schema', 'collected', 'properties', 'errors'} or
            type(record['schema']) is not int or record['schema'] != 1 or
            record['collected'] is not True or record['errors'] != [] or
            not isinstance(record['properties'], dict) or set(record['properties']) != set(FIELDS)):
        return ['Effective property evidence is missing, incomplete or malformed']
    try:
        for interface in FIELDS:
            validate_group(interface, record['properties'][interface])
    except ValueError as error:
        return [str(error)]
    unit = record['properties']['Unit']
    service = record['properties']['Service']
    # Repeat identity/staleness checks on this separate observation, and correlate
    # with the existing collector. This narrows mistakes; it is not an atomic read.
    expected_identity = dict(Id=metadata['Id'], FragmentPath=metadata['FragmentPath'],
                             SourcePath='', DropInPaths=[], NeedDaemonReload=False)
    for key, expected in expected_identity.items():
        if unit[key]['data'] != expected:
            reasons.append('Effective identity/override differs: ' + key)
    for interface, expected_fields in [('Unit', UNIT_EXPECTED), ('Service', SERVICE_EXPECTED)]:
        for name, (signature, expected) in expected_fields.items():
            value = record['properties'][interface][name]['data']
            # Only known nonempty string sets may reorder. Reject duplicates and
            # unrecognized quoting rather than interpreting shell-like syntax.
            matches = (len(value) == len(expected) and set(value) == set(expected)
                       if signature == 'as' else value == expected)
            if not matches:
                reasons.append('Effective property differs from retained-vm-v1: ' + name)
    conditions = unit['Conditions']['data']
    if (len(conditions) != 1 or not isinstance(conditions[0], list) or
            len(conditions[0]) != 5 or
            conditions[0][:4] != ['ConditionEnvironment', False, False, 'WAYLAND_DISPLAY'] or
            type(conditions[0][1]) is not bool or type(conditions[0][2]) is not bool or
            type(conditions[0][4]) is not int or conditions[0][4] not in (-1, 0, 1)):
        reasons.append('Effective environment condition differs or is malformed')
    commands = service['ExecStartEx']['data']
    if (len(commands) != 1 or not isinstance(commands[0], list) or len(commands[0]) != 10 or
            commands[0][:3] != [COMMAND, ARGV, []] or
            any(type(x) is not int or x < 0 for x in commands[0][3:]) or
            any(x > INFINITY for x in commands[0][3:7]) or commands[0][7] > 2**32-1 or
            any(x >= 2**31 for x in commands[0][8:])):
        reasons.append('Effective execution differs or is malformed')
    return reasons
