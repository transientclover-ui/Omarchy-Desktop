#!/usr/bin/env python3
"""Tests for atomic, non-sensitive Frankenstein state writes."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "src/libexec/frankenstein-state"


class StateTests(unittest.TestCase):
    def run_state(self, path: Path, *arguments: str):
        env = dict(os.environ, FRANKENSTEIN_STATE_FILE=str(path))
        return subprocess.run(
            [str(TOOL), *arguments],
            env=env,
            text=True,
            capture_output=True,
            timeout=5,
        )

    def test_install_then_background_preserves_operational_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state/sddm-state.json"
            first = self.run_state(
                path,
                "record-install",
                "--theme-active",
                "--previous-theme",
                "breeze",
                "--backup-location",
                "/var/lib/frankenstein/backups/example",
                "--configuration-path",
                "/etc/sddm.conf.d/zzzz-frankenstein.conf",
                "--session",
                "plasma.desktop",
                "--session",
                "omarchy.desktop",
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            data = json.loads(path.read_text())
            self.assertTrue(data["theme_active"])
            self.assertEqual(
                data["detected_sessions"], ["omarchy.desktop", "plasma.desktop"]
            )
            second = self.run_state(
                path,
                "record-background",
                "--selected-background",
                "/var/lib/frankenstein/backgrounds/selected.png",
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            updated = json.loads(path.read_text())
            self.assertEqual(updated["previous_theme"], "breeze")
            self.assertEqual(
                updated["selected_background"],
                "/var/lib/frankenstein/backgrounds/selected.png",
            )
            serialized = path.read_text().lower()
            for forbidden in ("password", "cookie", "token", "username"):
                self.assertNotIn(forbidden, serialized)

    def test_malformed_old_state_is_replaced_not_trusted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sddm-state.json"
            path.write_text("{broken")
            result = self.run_state(path, "record-install")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(path.read_text())["schema_version"], 1)


if __name__ == "__main__":
    unittest.main()
