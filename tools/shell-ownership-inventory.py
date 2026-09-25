#!/usr/bin/env python3
"""Conservative, offline inventory; never authorizes or performs migration."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import runpy
import stat

UNIT = 'omarchy-shell.service'
LINK = 'graphical-session.target.wants/' + UNIT
COMMAND = '/usr/bin/quickshell -n -p /usr/share/omarchy/shell'
# Exact reviewed VM shape, not a template for arbitrary user units. Keep the
# description literal too: generalizing syntax belongs to a separate review.
VM_SHAPE = [
    '[Unit]', 'Description=VM existing customized Omarchy shell',
    'After=graphical-session.target', 'PartOf=graphical-session.target',
    'ConditionEnvironment=WAYLAND_DISPLAY', '[Service]', 'Type=simple',
    'Environment=QS_DISABLE_FILE_WATCHER=1', 'Environment=QS_NO_RELOAD_POPUP=1',
    'ExecStart=' + COMMAND, 'Restart=on-failure', 'RestartSec=3',
    '[Install]', 'WantedBy=graphical-session.target',
]


def inspect(snapshot):
    result = {'schema': 1, 'scope': 'offline-directory-snapshot',
              'recognized_shape': False, 'migration_ready': False,
              'activation': 'unknown', 'entries': [], 'reasons': [],
              'unassessed': ['effective systemd unit and search paths',
                             'live session and process ownership',
                             'activation outside supplied directories']}
    reasons = result['reasons']
    contents = {}

    def walk(directory, prefix):
        # Do not follow links, including directory links, from the snapshot.
        for item in sorted(directory.iterdir()):
            relative = prefix + item.name
            info = item.lstat()
            entry = {'path': relative, 'mode': stat.S_IMODE(info.st_mode)}
            result['entries'].append(entry)
            if stat.S_ISLNK(info.st_mode):
                entry.update(kind='symlink', target=os.readlink(item))
                if relative == 'units/' + LINK and entry['target'] == '../' + UNIT:
                    result['activation'] = 'graphical-session.target'
                else:
                    reasons.append('Unsupported symlink: ' + relative)
            elif stat.S_ISDIR(info.st_mode):
                entry['kind'] = 'directory'
                if relative != 'units/graphical-session.target.wants':
                    reasons.append('Unsupported directory (including overrides): ' + relative)
                walk(item, relative + '/')
            elif stat.S_ISREG(info.st_mode):
                entry['kind'] = 'file'
                data = item.read_bytes()
                entry['sha256'] = hashlib.sha256(data).hexdigest()
                entry['size_bytes'] = len(data)
                if relative == 'units/' + UNIT:
                    contents[UNIT] = data.decode('utf-8')
                else:
                    reasons.append('Unassessed file may provide activation: ' + relative)
            else:
                entry['kind'] = 'special'
                reasons.append('Unsupported special file: ' + relative)

    try:
        if snapshot.is_symlink() or not snapshot.is_dir():
            raise ValueError('Snapshot must be a real directory')
        for name in ('units', 'autostart'):
            directory = snapshot / name
            if directory.is_symlink() or not directory.is_dir():
                raise ValueError('Missing or linked snapshot directory: ' + name)
            walk(directory, name + '/')
        unit = contents.get(UNIT)
        if unit is None:
            reasons.append('Missing regular ' + UNIT)
        else:
            # Recognize two exact reviewed shapes, not general systemd syntax.
            # Reject duplicates, continuations, wrappers and additional directives.
            lines = [line.strip(' \t\r') for line in unit.split('\n')
                     if line.strip(' \t\r') and
                     not line.lstrip(' \t').startswith(('#', ';'))]
            if lines not in (['[Service]', 'ExecStart=' + COMMAND], VM_SHAPE):
                reasons.append('Unit is outside the recognized direct-launch fixture shape')
            else:
                result['launch_command'] = COMMAND
                if lines == VM_SHAPE:
                    result['unit_shape'] = 'retained-vm-v1'
        if result['activation'] == 'unknown' and not reasons:
            result['activation'] = 'no-link-in-snapshot'
        result['recognized_shape'] = not reasons
    except (OSError, UnicodeError, ValueError) as error:
        reasons.append('Inventory incomplete: ' + str(error))
    return result



def compare_capture(result, capture_path, source_directory, require_effective=False):
    """Compare supplied observations only; source paths are never opened."""
    result['consistent_observations'] = False
    result['fragment_bytes_match'] = None
    result['source_unit_directory'] = source_directory
    if require_effective:
        result['effective_properties_match'] = False
    result['unassessed'].append('snapshot origin, capture freshness and manager-loaded bytes')
    reasons = result['reasons']
    try:
        source = PurePosixPath(source_directory)
        if (not source.is_absolute() or str(source) != source_directory or
                '..' in source.parts):
            raise ValueError('Source unit directory must be a canonical absolute POSIX path')
        if capture_path.is_symlink() or not capture_path.is_file():
            raise ValueError('Capture must be a regular, unlinked JSON file')
        def unique_fields(pairs):
            fields = {}
            for key, value in pairs:
                if key in fields:
                    raise ValueError('Duplicate JSON field: ' + key)
                fields[key] = value
            return fields
        capture = json.loads(capture_path.read_text(), object_pairs_hook=unique_fields)
        if (not isinstance(capture, dict) or type(capture.get('schema')) is not int or
                capture['schema'] != 1 or type(capture.get('collector_exit_status')) is not int or
                capture['collector_exit_status'] != 0 or
                type(capture.get('sanitized')) is not bool):
            raise ValueError('Unsupported or unsuccessful capture envelope')
        if require_effective or 'effective' in capture:
            result['effective_properties_match'] = False
        report = capture.get('report')
        if (not isinstance(report, dict) or type(report.get('schema')) is not int or
                type(report.get('metadata_collected')) is not bool or
                type(report.get('migration_ready')) is not bool):
            raise ValueError('Capture report must be an object')
        # Reassess the raw properties using the collector's existing rules.
        # run_path loads definitions only, without executing its CLI or writing pyc.
        metadata = runpy.run_path(str(Path(__file__).with_name('shell-ownership-metadata.py')))
        for name, fields in [('unit', metadata['PROPERTIES']), ('manager', ('UnitPath',))]:
            values = report.get(name)
            if (not isinstance(values, dict) or set(values) != set(fields) or
                    any(not isinstance(value, str) for value in values.values())):
                raise ValueError('Incomplete or invalid captured ' + name + ' properties')
        assessed = metadata['collect'](
            query_fn=lambda properties, unit=None: report['unit' if unit else 'manager'])
        if report != assessed:
            raise ValueError('Capture derived fields disagree with its raw properties')
        if assessed['reasons']:
            reasons.extend('Captured metadata: ' + reason for reason in assessed['reasons'])
        unit = report['unit']
        if unit['FragmentPath'] != str(source / UNIT):
            reasons.append('Captured fragment does not match the explicit source mapping')
        if source_directory not in report['search_paths']:
            reasons.append('Mapped source directory is absent from captured search paths')
        # Intentionally recognize only the observed single-command serialization.
        # Never evaluate argv[] or accept extra command records after the first one.
        launch = (r'\{ path=/usr/bin/quickshell ; argv\[\]=' + re.escape(COMMAND) +
                  r' ; ignore_errors=no ; start_time=\[[^\]\r\n]*\] ; '
                  r'stop_time=\[[^\]\r\n]*\] ; pid=[0-9]+ ; '
                  r'code=[^;{}\r\n]+ ; status=[^;{}\r\n]+ \}')
        if not re.fullmatch(launch, unit['ExecStart']):
            reasons.append('Captured launch command differs or has unsupported serialization')
        expected_activation = {'enabled': 'graphical-session.target',
                               'disabled': 'no-link-in-snapshot'}.get(unit['UnitFileState'])
        if result['activation'] != expected_activation:
            reasons.append('Snapshot activation disagrees with captured enablement')
        if 'fragment' in capture:
            result['fragment_bytes_match'] = False
            fragment = capture['fragment']
            entry = next((item for item in result['entries']
                          if item['path'] == 'units/' + UNIT and item['kind'] == 'file'), {})
            if (type(capture.get('capture_exit_status')) is not int or
                    capture['capture_exit_status'] != 0 or not isinstance(fragment, dict) or
                    fragment.get('outcome') != 'ok' or
                    fragment.get('path') != unit['FragmentPath'] or
                    not isinstance(fragment.get('sha256'), str) or
                    not re.fullmatch('[0-9a-f]{64}', fragment['sha256']) or
                    type(fragment.get('size_bytes')) is not int or
                    fragment['size_bytes'] != entry.get('size_bytes') or
                    fragment['sha256'] != entry.get('sha256')):
                reasons.append('Fragment provenance is refused, invalid or differs from snapshot bytes')
            else:
                result['fragment_bytes_match'] = True
        if require_effective or 'effective' in capture:
            result['unassessed'].append(
                'inherited process environment, unqueried properties and changes between property reads')
            if result.get('unit_shape') != 'retained-vm-v1':
                reasons.append('Effective comparison requires the retained-vm-v1 snapshot shape')
            if result['fragment_bytes_match'] is not True:
                reasons.append('Effective comparison requires matching fragment-byte evidence')
            if type(capture.get('capture_exit_status')) is not int or capture['capture_exit_status'] != 0:
                reasons.append('Effective comparison requires successful full capture')
            effective = runpy.run_path(str(Path(__file__).with_name('shell-effective-properties.py')))
            reasons.extend(effective['assess'](capture.get('effective'), unit))
            result['effective_properties_match'] = result['recognized_shape'] and not reasons
        result['consistent_observations'] = result['recognized_shape'] and not reasons
    except (OSError, UnicodeError, ValueError) as error:
        reasons.append('Capture comparison refused: ' + str(error))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path,
                        help='offline directory containing units/ and autostart/')
    parser.add_argument('--capture', type=Path, help='saved metadata capture JSON')
    parser.add_argument('--source-unit-directory',
                        help='original absolute path represented by snapshot units/')
    parser.add_argument('--require-effective', action='store_true',
                        help='require matching typed effective properties and fragment provenance')
    args = parser.parse_args()
    if (args.capture is None) != (args.source_unit_directory is None):
        parser.error('--capture and --source-unit-directory must be supplied together')
    if args.require_effective and args.capture is None:
        parser.error('--require-effective requires --capture and --source-unit-directory')
    result = inspect(args.snapshot)
    if args.capture is not None:
        result = compare_capture(result, args.capture, args.source_unit_directory, args.require_effective)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get('consistent_observations', result['recognized_shape']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
