#!/usr/bin/env python3
"""Capture metadata on a disposable guest; writes private local evidence only."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='new evidence JSON file (never overwritten)')
    args = parser.parse_args()
    collector = Path(__file__).with_name('shell-ownership-metadata.py')
    try:
        result = subprocess.run([sys.executable, str(collector)], capture_output=True,
                                text=True, timeout=15, check=False)
        if result.returncode not in (0, 1):
            raise ValueError('Collector did not complete normally')
        report = json.loads(result.stdout)
        if (report.get('schema') != 1 or report.get('scope') != 'user-systemd-metadata'
                or report.get('migration_ready') is not False):
            raise ValueError('Unexpected collector report')
        evidence = {'schema': 1, 'collector_exit_status': result.returncode,
                    'sanitized': False, 'report': report}
        # Exclusive creation prevents clobbering files or following a final symlink.
        # The caller supplies a private, stable parent directory in the guest.
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(evidence, stream, indent=2, sort_keys=True)
            stream.write('\n')
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('Capture failed: ' + type(error).__name__, file=sys.stderr)
        return 2
    print('Private evidence saved; review and sanitize before sharing.')
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
