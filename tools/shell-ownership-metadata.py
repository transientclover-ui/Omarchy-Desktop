#!/usr/bin/env python3
"""Collect read-only user-manager metadata; never authorizes migration."""
import argparse
import json
import os
import subprocess

UNIT = 'omarchy-shell.service'
PROPERTIES = ('Id', 'Names', 'LoadState', 'UnitFileState', 'FragmentPath',
              'SourcePath', 'DropInPaths', 'ActiveState', 'SubState',
              'NeedDaemonReload', 'ExecStart')


def query(properties, unit=None):
    command = ['systemctl', '--user', '--no-pager', 'show', '--all',
               '--property=' + ','.join(properties)]
    if unit:
        command.append(unit)
    completed = subprocess.run(command, capture_output=True, text=True,
                               timeout=5, check=True,
                               env=dict(os.environ, LC_ALL='C', SYSTEMD_COLORS='0'))
    values = {}
    for line in completed.stdout.splitlines():
        key, separator, value = line.partition('=')
        if not separator or key not in properties or key in values:
            raise ValueError('Unexpected, duplicate or malformed property output')
        values[key] = value
    if set(values) != set(properties):
        raise ValueError('Missing requested properties')
    return values


def collect(query_fn=query):
    report = {'schema': 1, 'scope': 'user-systemd-metadata',
              'metadata_collected': False, 'migration_ready': False,
              'unit': {}, 'manager': {}, 'search_paths': [], 'reasons': [],
              'unassessed': ['unit contents and dependency semantics',
                             'activation files within and outside search paths',
                             'live session and process ownership',
                             'concurrent changes between queries']}
    for key, properties, unit in [('unit', PROPERTIES, UNIT),
                                  ('manager', ('UnitPath',), None)]:
        try:
            report[key] = query_fn(properties, unit)
        except (OSError, UnicodeError, subprocess.SubprocessError, ValueError) as error:
            # Do not include command output: it may contain private unit values.
            report['reasons'].append(key + ' query failed: ' + type(error).__name__)
    if not report['unit'] or not report['manager']:
        return report
    report['metadata_collected'] = True
    values = report['unit']
    reasons = report['reasons']
    if values['Id'] != UNIT or values['Names'].split() != [UNIT]:
        reasons.append('Unexpected unit identity or aliases require review')
    if values['LoadState'] != 'loaded':
        reasons.append('Unit is not loaded: ' + values['LoadState'])
    if values['UnitFileState'] not in ('enabled', 'disabled'):
        reasons.append('Unsupported unit-file state: ' + values['UnitFileState'])
    if not values['FragmentPath'].startswith('/') or values['FragmentPath'] == '/dev/null':
        reasons.append('Missing or masked unit fragment')
    if values['SourcePath']:
        reasons.append('Generated/source-backed unit requires review')
    if values['DropInPaths']:
        reasons.append('Drop-ins require review')
    if values['NeedDaemonReload'] != 'no':
        reasons.append('Manager configuration may be stale')
    if (values['ActiveState'], values['SubState']) not in (
            ('active', 'running'), ('inactive', 'dead')):
        reasons.append('Failed, transitional or unsupported runtime state')
    if not values['ExecStart']:
        reasons.append('Launch command metadata is missing')
    # Keep the original serialization. Do not guess escaped/quoted path syntax.
    paths = report['manager']['UnitPath']
    if (not paths or any(char in paths for char in '\\"\'\t') or
            any(not path.startswith('/') for path in paths.split(' '))):
        reasons.append('Search-path serialization is empty or unsupported')
    else:
        report['search_paths'] = paths.split(' ')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    report = collect()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['metadata_collected'] and not report['reasons'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
