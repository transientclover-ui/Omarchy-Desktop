#!/usr/bin/env python3
"""Explicit disposable-QEMU harness; run beside copies of the existing tools."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

if sys.argv[1:] != ['--disposable-guest']:
    raise SystemExit('Requires --disposable-guest inside the disposable QEMU guest')
if 'QEMU' not in Path('/sys/class/dmi/id/sys_vendor').read_text():
    raise SystemExit('Refusing non-QEMU system')
base = Path(__file__).resolve().parent
out = base / 'results'
out.mkdir(mode=0o700)
unit = Path.home() / '.config/systemd/user/omarchy-shell.service'
config = Path.home() / '.config/omarchy/shell.json'
original = unit.read_bytes()
info = unit.stat()
def hashes():
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (unit, config)}
before = hashes()
snap = out / 'snapshot'
(snap / 'units/graphical-session.target.wants').mkdir(parents=True)
(snap / 'autostart').mkdir()
(snap / 'units/omarchy-shell.service').write_bytes(original)
(snap / 'units/graphical-session.target.wants/omarchy-shell.service').symlink_to('../omarchy-shell.service')
wrapper = out / 'bin'
wrapper.mkdir()
# All replies come from real guest busctl. Change only after the last initial
# mount query has returned, before the first repeated query can start.
(wrapper / 'busctl').write_text('''#!/usr/bin/python3
import json, os, subprocess, sys, time
from pathlib import Path
r = subprocess.run(['/usr/bin/busctl', *sys.argv[1:]], capture_output=True)
marker = Path(os.environ['COHERENCE_MARKER'])
if (r.returncode == 0 and sys.argv[-1] == 'Where' and
        '/org/freedesktop/systemd1/unit/_2d_2emount' in sys.argv and not marker.exists()):
    unit = Path(os.environ['COHERENCE_UNIT'])
    with unit.open('ab') as stream:
        stream.write(b'\\n# Disposable coherence validation change\\n')
        stream.flush()
        os.fsync(stream.fileno())
    marker.write_text(json.dumps({'trigger': sys.argv[1:], 'monotonic_ns': time.monotonic_ns(), 'action': 'append comment after first RootMount reply'}))
sys.stdout.buffer.write(r.stdout)
sys.stderr.buffer.write(r.stderr)
raise SystemExit(r.returncode)
''')
(wrapper / 'busctl').chmod(0o700)
validation = {'systemd': subprocess.check_output(['systemctl', '--version'], text=True).splitlines()[0], 'before_hashes': before, 'cases': {}}
try:
    for name in ('stable', 'changed'):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        if name == 'changed':
            env.update(PATH=str(wrapper) + ':' + env['PATH'], COHERENCE_UNIT=str(unit), COHERENCE_MARKER=str(out / 'mutation.json'))
        evidence = out / (name + '.json')
        result = subprocess.run([sys.executable, str(base / 'capture-shell-ownership-metadata.py'), str(evidence), '--hash-fragment', '--effective-properties', '--mount-context', '--check-coherence'], capture_output=True, text=True, env=env, timeout=150)
        (out / (name + '-output.txt')).write_text(result.stdout + result.stderr)
        capture = json.loads(evidence.read_text())
        comparison = subprocess.run([sys.executable, str(base / 'shell-ownership-inventory.py'), str(snap), '--capture', str(evidence), '--source-unit-directory', str(unit.parent), '--require-effective', '--mount-home', str(Path.home()), '--require-coherence'], capture_output=True, text=True, timeout=20)
        (out / (name + '-comparison.json')).write_text(comparison.stdout)
        report = json.loads(comparison.stdout)
        validation['cases'][name] = {'capture_exit': result.returncode, 'comparison_exit': comparison.returncode, 'evidence_mode': oct(evidence.stat().st_mode & 0o777), 'hashes_after': hashes()}
        assert report['migration_ready'] is False
        assert comparison.returncode == 1
        assert 'Effective property differs from retained-vm-v1: After' in report['reasons']
        assert capture['coherence']['agrees'] is (name == 'stable'), capture['coherence']['errors']
        assert result.returncode == (0 if name == 'stable' else 1)
        assert report['capture_coherence_agrees'] is (name == 'stable')
        if name == 'changed':
            assert (out / 'mutation.json').exists()
            assert capture['fragment']['sha256'] != capture['coherence']['after']['fragment']['sha256']
finally:
    unit.write_bytes(original)
    os.utime(unit, ns=(info.st_atime_ns, info.st_mtime_ns))
    validation['restored_hashes'] = hashes()
    (out / 'validation.json').write_text(json.dumps(validation, indent=2) + '\n')
assert before == hashes()
print('COHERENCE VALIDATION FINISHED: stable agreement; changed refusal; bytes restored')
