#!/usr/bin/env python3
"""Conservative, offline inventory; never authorizes or performs migration."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

UNIT = 'omarchy-shell.service'
LINK = 'graphical-session.target.wants/' + UNIT
COMMAND = '/usr/bin/quickshell -n -p /usr/share/omarchy/shell'


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
            # Recognize the existing test fixture only, not general systemd syntax.
            # Reject duplicates, continuations, wrappers and additional directives.
            lines = [line.strip() for line in unit.splitlines()
                     if line.strip() and not line.lstrip().startswith(('#', ';'))]
            if lines != ['[Service]', 'ExecStart=' + COMMAND]:
                reasons.append('Unit is outside the recognized direct-launch fixture shape')
            else:
                result['launch_command'] = COMMAND
        if result['activation'] == 'unknown' and not reasons:
            result['activation'] = 'no-link-in-snapshot'
        result['recognized_shape'] = not reasons
    except (OSError, UnicodeError, ValueError) as error:
        reasons.append('Inventory incomplete: ' + str(error))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path,
                        help='offline directory containing units/ and autostart/')
    args = parser.parse_args()
    result = inspect(args.snapshot)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['recognized_shape'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
