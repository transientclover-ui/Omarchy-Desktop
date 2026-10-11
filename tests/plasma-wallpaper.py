#!/usr/bin/env python3
"""Exercise session transitions and preservation in isolated user directories."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

SCRIPT = Path(__file__).resolve().parents[1] / 'src/bin/frankenstein-plasma-wallpaper'
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    config = root / 'config/omarchy/shell.json'
    config.parent.mkdir(parents=True)
    env = dict(os.environ, XDG_CONFIG_HOME=str(root / 'config'), XDG_STATE_HOME=str(root / 'state'),
               XDG_CURRENT_DESKTOP='vendor:KDE', XDG_SESSION_TYPE='wayland')
    original = {'bar': {'layout': {'right': [{'id': 'custom.plugin'}]}}, 'disabledPlugins': ['omarchy.lock']}
    def run(command, desktop='vendor:KDE', session='wayland', good=True):
        result = subprocess.run([str(SCRIPT), command], env=dict(env, XDG_CURRENT_DESKTOP=desktop,
                                 XDG_SESSION_TYPE=session), capture_output=True, text=True)
        assert (result.returncode == 0) == good, result.stderr
    config.write_text(json.dumps(original))
    run('session')
    changed = json.loads(config.read_text())
    assert changed['disabledPlugins'] == ['omarchy.lock', 'omarchy.background']
    assert changed['bar'] == original['bar']
    backups = list((root / 'state').rglob('shell-*.json'))
    assert len(backups) == 1 and json.loads(backups[0].read_text()) == original
    run('session')
    assert len(list((root / 'state').rglob('shell-*.json'))) == 1
    changed['newUserSetting'] = True
    config.write_text(json.dumps(changed))
    run('session', 'Hyprland')
    assert json.loads(config.read_text()) == dict(original, newUserSetting=True)
    # A background disable that predates this fix belongs to the user.
    original['disabledPlugins'].append('omarchy.background')
    config.write_text(json.dumps(original))
    run('session')
    run('restore')
    assert json.loads(config.read_text()) == original
    config.write_text('{"bar":{}}')
    run('session', session='x11')
    assert json.loads(config.read_text()) == {'bar': {}}
    run('session')
    run('restore')
    assert json.loads(config.read_text()) == {'bar': {}}
    # Exercise the opt-in command through mocked external services.
    mock = root / 'mock'
    mock.mkdir()
    for name, body in {'systemctl': 'exit 0', 'omarchy-shell': 'echo ok'}.items():
        executable = mock / name
        executable.write_text('#!/bin/sh\n' + body + '\n')
        executable.chmod(0o755)
    env['PATH'] = str(mock) + ':' + env['PATH']
    run('install')
    dropin = root / 'config/systemd/user/omarchy-shell.service.d/50-frankenstein-wallpaper.conf'
    assert 'ExecStartPre=' in dropin.read_text() and 'ExecStopPost=' in dropin.read_text()
    run('install')
    run('remove')
    assert not dropin.exists() and json.loads(config.read_text()) == {'bar': {}}
    (mock / 'omarchy-shell').write_text('#!/bin/sh\necho unknown\n')
    run('install', good=False)
    assert 'omarchy.background' in json.loads(config.read_text())['disabledPlugins']
    run('remove')
    config.write_text('{broken')
    run('session', good=False)
    assert config.read_text() == '{broken'
    run('install', desktop='Hyprland', good=False)
    assert not dropin.exists()
print('PASS: Plasma/Hyprland/X11 transitions, backups, idempotency, user preferences and invalid config')
