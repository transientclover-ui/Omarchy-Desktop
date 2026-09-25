#!/usr/bin/env python3
"""Capture metadata on a disposable guest; writes private local evidence only."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys



MAX_FRAGMENT_BYTES = 1024 * 1024


def open_fragment(path):
    """Open an absolute file without following symlinks in any component."""
    parts = PurePosixPath(path)
    if (not parts.is_absolute() or str(parts) != path or
            '..' in parts.parts or len(parts.parts) < 2):
        raise ValueError('noncanonical-path')
    parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for name in parts.parts[1:-1]:
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=parent)
            os.close(parent)
            parent = child
        return os.open(parts.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                       dir_fd=parent)
    finally:
        os.close(parent)


def fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_mode, info.st_uid, info.st_gid)


def fragment_provenance(path):
    result = {'path': path, 'outcome': 'refused'}
    if not isinstance(path, str):
        result['reason'] = 'invalid-path-type'
        return result
    try:
        fd = open_fragment(path)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                raise ValueError('not-regular')
            if before.st_size > MAX_FRAGMENT_BYTES:
                raise ValueError('too-large')
            digest = hashlib.sha256()
            total = 0
            while True:
                block = os.read(fd, min(65536, MAX_FRAGMENT_BYTES + 1 - total))
                if not block:
                    break
                total += len(block)
                if total > MAX_FRAGMENT_BYTES:
                    raise ValueError('too-large')
                digest.update(block)
            after = os.fstat(fd)
        finally:
            os.close(fd)
        # Rewalk the original path to catch replacements, including parent swaps.
        current_fd = open_fragment(path)
        try:
            current = os.fstat(current_fd)
        finally:
            os.close(current_fd)
        if (fingerprint(before) != fingerprint(after) or
                fingerprint(after) != fingerprint(current) or total != before.st_size):
            raise ValueError('changed-during-read')
        result.update(outcome='ok', sha256=digest.hexdigest(), size_bytes=total)
    except ValueError as error:
        result['reason'] = str(error)
    except OSError as error:
        result['reason'] = 'read-error'
        result['errno'] = error.errno
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='new evidence JSON file (never overwritten)')
    parser.add_argument('--hash-fragment', action='store_true',
                        help='also read/hash the captured on-disk fragment (no symlinks)')
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
        capture_status = result.returncode
        if args.hash_fragment:
            if report.get('metadata_collected') is not True:
                evidence['fragment'] = {'outcome': 'refused', 'reason': 'metadata-incomplete'}
            else:
                evidence['fragment'] = fragment_provenance(report.get('unit', {}).get('FragmentPath'))
            if evidence['fragment']['outcome'] != 'ok':
                capture_status = 1
            evidence['capture_exit_status'] = capture_status
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
    return capture_status


if __name__ == '__main__':
    raise SystemExit(main())
