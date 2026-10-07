#!/usr/bin/env python3
"""Exercise adapter boundaries without touching the session or installation."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = (Path(__file__).resolve().parents[1] / 'src/bin/frankenstein-shell-adapter').read_text()
FUNCTIONS = SOURCE[SOURCE.index('desktop_environment() {'):SOURCE.index('open_terminal() {')]

class SessionBoundaries(unittest.TestCase):
    def run_bash(self, desktop, body, display=None):
        env = dict(os.environ, XDG_CURRENT_DESKTOP=desktop)
        env.pop('WAYLAND_DISPLAY', None)
        if display is not None:
            env['WAYLAND_DISPLAY'] = display
        return subprocess.run(['bash', '-c', 'set -euo pipefail\n' + FUNCTIONS + '\n' + body], env=env, text=True, capture_output=True)

    def test_profile_launch_accepts_desktop_list(self):
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, 'plasma.json').write_text('{}')
            launcher = Path(directory, 'quickshell')
            launcher.write_text('#!/bin/sh\nprintf "launched:%s" "$FRANKENSTEIN_SHELL_PROFILE"\n')
            launcher.chmod(0o755)
            body = f'profile_dir={directory}\nshell_dir=/shell\ndisabled_file={directory}/disabled\n' + """
profile_value() {
 case "$2" in
 '.desktop') echo KDE ;;
 '.shell.enabledPlugins | join(",")') echo omarchy.menu ;;
 *) echo 1 ;;
 esac
}
"""
            for desktop, accepted in [('KDE', True), ('KDE:custom', True), ('custom:KDE', True), ('Hyprland', False), ('KDEish', False)]:
                env = dict(os.environ, XDG_CURRENT_DESKTOP=desktop, PATH=directory + ':' + os.environ['PATH'])
                result = subprocess.run(['bash', '-c', 'set -euo pipefail\n' + FUNCTIONS + body + '\nrun_shell plasma'], env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, accepted, result.stderr)
                if accepted:
                    self.assertEqual(result.stdout, 'launched:plasma')

    def test_profile_detection_uses_desktop_tokens(self):
        for desktop in ('KDE', 'KDE:custom', 'custom:KDE', 'custom:KDE:other'):
            result = self.run_bash(desktop, 'profile_for_desktop')
            self.assertEqual(result.stdout.strip(), 'plasma')
        for desktop in ('Hyprland', 'KDEish'):
            self.assertNotEqual(self.run_bash(desktop, 'profile_for_desktop').returncode, 0)

    def test_filtered_health_plugin_boundaries(self):
        check_function = SOURCE[SOURCE.index('check() {'):SOURCE.index('set_bar_mode() {')]
        mocks = """
service=test.service
shell_dir=/shell
disabled_file=/missing
profile_value() {
 case "$2" in
 '.desktop') echo KDE ;;
 '.shell.panel') echo omarchy ;;
 '.shell.enabledPlugins') echo '[]' ;;
 esac
}
pgrep() { echo 1; }
systemctl() { echo active; }
busctl() { :; }
ipc() {
 case "$*" in
 'shell ping') echo ok ;;
 'shell listPlugins') printf '%s' "$TEST_PLUGINS" ;;
 'shell barStatus') echo '{"loaded":true,"hidden":false}' ;;
 esac
}
"""
        for plugins, healthy in [
            ('[{"id":"omarchy.bar","enabled":true,"firstParty":true}]', True),
            ('[{"id":"hyprland.only","enabled":true,"firstParty":true}]', False),
            ('garbage', False),
            ('', False),
        ]:
            env = dict(os.environ, XDG_CURRENT_DESKTOP='custom:KDE', TEST_PLUGINS=plugins)
            result = subprocess.run(['bash', '-c', 'set -euo pipefail\n' + FUNCTIONS + check_function + mocks + '\ncheck'], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode == 0, healthy, result.stdout + result.stderr)

    def test_missing_display_does_not_call_ipc(self):
        result = self.run_bash('KDE', 'timeout() { echo unsafe; }; ipc shell ping')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('unsafe', result.stdout)
        self.assertIn('refusing cross-session IPC', result.stderr)

    def test_explicit_display_is_preserved(self):
        result = self.run_bash('KDE', 'shell_dir=/shell; timeout() { echo "$WAYLAND_DISPLAY"; }; ipc shell ping', 'wayland-7')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'wayland-7')

if __name__ == '__main__':
    unittest.main()
