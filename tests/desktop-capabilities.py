#!/usr/bin/env python3
"""Provider regressions use fixtures, never dispatch live desktop actions."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('capabilities', str(ROOT / 'src/bin/frankenstein-capabilities'))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


class Fake(m.Probe):
    def __init__(self, desktop='KDE', live='KDE'):
        super().__init__({'XDG_CURRENT_DESKTOP': desktop, 'XDG_SESSION_TYPE': 'wayland', 'HOME': '/test'})
        self.live = {'Desktop': live, 'Type': 'wayland', 'Active': 'yes', 'User': str(os.getuid())}
        self.owners = {'org.kde.KWin': ':1.1', 'org.freedesktop.Notifications': ':1.2', 'org.freedesktop.ScreenSaver': ':1.3'}
        self.connected = True
        self.kwin_matches = True
        self.hypr = False
        self.missing = set()
        self.modules = 'kcm_kscreen\nkcm_keys\nkcm_mouse\nkcm_nightlight\nkcm_kwin_virtualdesktops'
        self.plugins = '[{"id":"omarchy.lock","enabled":true}]'

    def utility(self, name): return None if name in self.missing else '/fixture/' + name
    def run(self, argv):
        if argv[0] == 'kcmshell6': return self.modules
        if argv[0] == 'qs': return self.plugins
        return None
    def owner(self, name): return self.owners.get(name)
    def wayland(self): return self.connected
    def session(self): return self.live
    def kwin_matches_wayland(self): return self.kwin_matches
    def hyprland(self): return self.hypr


def hyprland():
    p = Fake('Hyprland', 'Hyprland')
    p.owners.pop('org.kde.KWin')
    p.hypr = True
    return p


class Capabilities(unittest.TestCase):
    def test_normalize(self):
        for value in ('KDE', 'Other:KDE', 'KDE:Other', 'other:kde'):
            self.assertEqual(m.normalize(value), 'plasma')
        self.assertEqual(m.normalize('Hyprland'), 'hyprland')
        self.assertEqual(m.normalize('KDE:Hyprland'), 'ambiguous')
        self.assertEqual(m.normalize('KDEish'), 'unknown')
        self.assertEqual(m.normalize('GNOME'), 'gnome')

    def test_plasma_and_fixed_actions(self):
        p = Fake('Other:KDE')
        registry = m.detect(p)
        self.assertEqual(registry['desktop'], 'plasma')
        self.assertEqual(m.plan(registry, 'screenshots', '/test')['argv'], ['spectacle'])
        self.assertEqual(m.plan(registry, 'displays', '/test')['argv'], ['systemsettings', 'kcm_kscreen'])
        self.assertEqual(m.plan(registry, 'locking', '/test')['argv'][-1], 'Lock')
        self.assertEqual(m.plan(registry, 'input', '/test')['argv'][-1], 'kcm_mouse')
        self.assertEqual(registry['capabilities']['notifications']['owner'], ':1.2')
        self.assertEqual(registry['capabilities']['polkit']['state'], 'unknown')
        self.assertEqual(m.plan(registry, '$(touch /tmp/no)', '/test')['state'], 'unsupported')

    def test_hyprland_preserves_original_commands(self):
        registry = m.detect(hyprland())
        expected = {'locking': 'omarchy-system-lock', 'screenshots': 'omarchy-capture-screenshot',
                    'night-light': 'omarchy-toggle-nightlight', 'shortcuts': 'omarchy-launch-config-editor'}
        for action, command in expected.items():
            self.assertEqual(m.plan(registry, action, '/test')['argv'][0], command)
        self.assertEqual(m.plan(registry, 'workspaces', '/test')['argv'], ['hyprctl', '-j', 'workspaces'])

    def test_missing_dependencies_modules_and_services(self):
        p = Fake(); p.missing.add('spectacle'); p.modules = ''
        registry = m.detect(p)
        for action in ('screenshots', 'displays'):
            self.assertEqual(m.plan(registry, action, '/test')['state'], 'unavailable')
        p.owners.pop('org.freedesktop.ScreenSaver')
        p.owners.pop('org.freedesktop.Notifications')
        registry = m.detect(p)
        self.assertEqual(registry['capabilities']['locking']['state'], 'unavailable')
        self.assertEqual(registry['capabilities']['notifications']['state'], 'unsupported')
        p = hyprland(); p.plugins = 'not json'
        self.assertEqual(m.detect(p)['capabilities']['locking']['state'], 'unavailable')
        p = hyprland(); p.missing.add('hyprsunset')
        self.assertEqual(m.detect(p)['capabilities']['night_light']['state'], 'unavailable')

    def test_ambiguous_stale_and_switching_without_cache(self):
        p = Fake('Hyprland', 'KDE')
        self.assertEqual(m.detect(p)['desktop'], 'ambiguous')
        p.env['XDG_CURRENT_DESKTOP'] = 'KDE:Hyprland'
        self.assertEqual(m.detect(p)['desktop'], 'ambiguous')
        p.env['XDG_CURRENT_DESKTOP'] = 'KDE'; p.hypr = True
        self.assertEqual(m.detect(p)['desktop'], 'ambiguous')
        p.hypr = False; p.live['Active'] = 'no'
        self.assertEqual(m.detect(p)['desktop'], 'unknown')
        p.live['Active'] = 'yes'; p.connected = False
        self.assertEqual(m.detect(p)['desktop'], 'unknown')
        p.connected = True; p.kwin_matches = False
        self.assertEqual(m.detect(p)['desktop'], 'unknown')
        p.kwin_matches = True; p.env.pop('XDG_CURRENT_DESKTOP')
        self.assertEqual(m.detect(p)['desktop'], 'plasma')
        p.env['XDG_CURRENT_DESKTOP'] = 'Hyprland'; p.live['Desktop'] = 'Hyprland'
        p.owners.pop('org.kde.KWin'); p.hypr = True
        self.assertEqual(m.detect(p)['desktop'], 'hyprland')

    def test_future_gnome_is_explicitly_unsupported(self):
        p = Fake('GNOME', 'GNOME'); p.owners = {}
        registry = m.detect(p)
        self.assertEqual(registry['desktop'], 'gnome')
        self.assertNotEqual(m.plan(registry, 'locking', '/test')['state'], 'supported')

    def test_probe_timeout_and_absent_utilities(self):
        p = m.Probe({'PATH': ''})
        self.assertIsNone(p.run(['busctl']))
        with patch.object(p, 'utility', return_value='/fake'), patch.object(m.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fake', 2)):
            self.assertIsNone(p.run(['fake']))

    def test_kwin_socket_owner_matching(self):
        p = m.Probe({})
        p.wayland_peer = (42, os.getuid(), os.getgid())
        with patch.object(p, 'run', return_value='u 42'):
            self.assertTrue(p.kwin_matches_wayland())
        with patch.object(p, 'run', return_value='u 999999999'):
            self.assertFalse(p.kwin_matches_wayland())
        p.wayland_peer = (42, os.getuid() + 1, os.getgid())
        with patch.object(p, 'run', return_value='u 42'):
            self.assertFalse(p.kwin_matches_wayland())

    def test_socket_and_instance_match(self):
        with tempfile.TemporaryDirectory() as d:
            p = m.Probe({'XDG_RUNTIME_DIR': d, 'WAYLAND_DISPLAY': 'wayland-test', 'HYPRLAND_INSTANCE_SIGNATURE': 'test'})
            path = Path(d) / 'hypr/test/.socket.sock'; path.parent.mkdir(parents=True)
            with socket.socket(socket.AF_UNIX) as ipc, socket.socket(socket.AF_UNIX) as wl:
                ipc.bind(str(path)); wl.bind(str(Path(d) / 'wayland-test')); wl.listen()
                self.assertTrue(p.wayland())
                responses = [json.dumps([{'instance': 'test', 'wl_socket': 'wayland-test'}]), '[{"name":"test"}]']
                with patch.object(p, 'run', side_effect=responses): self.assertTrue(p.hyprland())
                with patch.object(p, 'run', return_value='[{"instance":"test","wl_socket":"stale"}]'):
                    self.assertFalse(p.hyprland())
                p.env['WAYLAND_DISPLAY'] = 'missing'
                self.assertFalse(p.wayland())

    def test_plan_never_dispatches_and_failure_is_json(self):
        with patch.object(m, 'Probe', return_value=Fake()), patch.object(m.sys, 'argv', ['caps','action','locking','--plan']), patch.object(m.subprocess,'Popen') as launch, patch.object(m.subprocess,'run') as run:
            self.assertEqual(m.main(), 0); launch.assert_not_called(); run.assert_not_called()
        with patch.object(m, 'Probe', return_value=Fake()), patch.object(m.sys, 'argv', ['caps','action','locking']), patch.object(m.subprocess,'run', side_effect=subprocess.TimeoutExpired('busctl',5)):
            self.assertEqual(m.main(), 4)
        with patch.object(m, 'Probe', return_value=Fake()), patch.object(m.sys, 'argv', ['caps','action','screenshots']), patch.object(m.subprocess,'Popen',side_effect=FileNotFoundError('gone')):
            self.assertEqual(m.main(), 4)

if __name__ == '__main__': unittest.main()
