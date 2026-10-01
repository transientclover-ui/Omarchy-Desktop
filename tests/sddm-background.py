#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Frankenstein contributors
# SPDX-License-Identifier: MIT

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
THEME = PROJECT / "src/sddm/frankenstein"
WRITER = PROJECT / "src/libexec/frankenstein-background-writer"
IMPORTER = PROJECT / "src/bin/frankenstein-background"


class BackgroundTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix=".sddm-background.", dir=PROJECT / "tests"))
        self.addCleanup(shutil.rmtree, self.work, ignore_errors=True)

    def fixture_root(self):
        root = self.work / "root"
        theme = root / "usr/share/sddm/themes/frankenstein"
        (theme / "backgrounds").mkdir(parents=True)
        shutil.copy2(THEME / "Main.qml", theme / "Main.qml")
        shutil.copy2(
            THEME / "backgrounds/vaporwave-default.png",
            theme / "backgrounds/vaporwave-default.png",
        )
        return root

    def tool_dir(self, mime="image/png", identify="PNG 64 32"):
        tools = self.work / "tools"
        tools.mkdir(exist_ok=True)
        for name, output in (("file", mime), ("identify", identify), ("magick", identify)):
            script = tools / name
            script.write_text(f"#!/bin/sh\nprintf '%s\\n' '{output}'\n")
            script.chmod(0o755)
        return tools

    def writer_env(self, root, tools):
        env = os.environ.copy()
        env.update(
            {
                "FRANKENSTEIN_BACKGROUND_TEST_MODE": "1",
                "FRANKENSTEIN_BACKGROUND_FIXTURE_ROOT": str(root),
                "PATH": f"{tools}:{env['PATH']}",
            }
        )
        return env

    def test_theme_has_session_picker_and_safe_fallback(self):
        qml = (THEME / "Main.qml").read_text()
        self.assertIn("model: sessionModel", qml)
        self.assertIn("Selected: %1", qml)
        self.assertIn("sddm.login", qml)
        self.assertIn("KeyNavigation.tab", qml)
        self.assertIn("/var/lib/sddm/.config/frankenstein/background.ini", qml)
        self.assertIn("/var/lib/frankenstein/backgrounds/", qml)
        self.assertIn("status === Image.Error", qml)
        self.assertIn("root.activeBackground = root.defaultBackground", qml)
        self.assertNotIn("Omarchy", qml)
        self.assertTrue((THEME / "backgrounds/vaporwave-default.png").is_file())

    def test_writer_stages_content_and_updates_fixed_override(self):
        root = self.fixture_root()
        tools = self.tool_dir()
        image = self.work / "chosen.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\nfixture")
        result = subprocess.run(
            [WRITER, image],
            env=self.writer_env(root, tools),
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertRegex(
            result.stdout.strip(),
            r"^/var/lib/frankenstein/backgrounds/[0-9a-f]{64}\.png$",
        )
        relative = result.stdout.strip().removeprefix("/")
        installed = root / relative
        self.assertEqual(installed.read_bytes(), image.read_bytes())
        self.assertEqual(installed.stat().st_mode & 0o777, 0o644)
        override = (root / "usr/share/sddm/themes/frankenstein/theme.conf.user").read_text()
        self.assertIn("backgrounds=backgrounds/vaporwave-default.png,", override)
        self.assertIn(result.stdout.strip(), override)

    def test_writer_refuses_symlink_and_mime_mismatch(self):
        root = self.fixture_root()
        tools = self.tool_dir(mime="image/jpeg", identify="JPEG 64 32")
        image = self.work / "chosen.png"
        image.write_bytes(b"not png")
        linked = self.work / "linked.png"
        linked.symlink_to(image)
        env = self.writer_env(root, tools)
        symlink = subprocess.run([WRITER, linked], env=env, text=True, capture_output=True)
        mismatch = subprocess.run([WRITER, image], env=env, text=True, capture_output=True)
        self.assertNotEqual(symlink.returncode, 0)
        self.assertIn("non-symlink", symlink.stderr)
        self.assertNotEqual(mismatch.returncode, 0)
        self.assertIn("MIME type do not agree", mismatch.stderr)

    def test_importer_uses_gui_and_writes_atomic_evidence(self):
        tools = self.work / "import-tools"
        tools.mkdir()
        image = self.work / "picked.webp"
        image.write_bytes(b"fixture")
        installed = "/var/lib/frankenstein/backgrounds/abc.webp"

        kdialog = tools / "kdialog"
        kdialog.write_text(f"#!/bin/sh\nprintf '%s\\n' '{image}'\n")
        kdialog.chmod(0o755)
        pkexec = tools / "pkexec"
        pkexec.write_text(
            "#!/bin/sh\n"
            'test "$1" = "$EXPECTED_HELPER" || exit 41\n'
            'printf "%s\\n" "$EXPECTED_INSTALLED"\n'
        )
        pkexec.chmod(0o755)
        helper = self.work / "writer"
        helper.write_text("#!/bin/sh\nexit 99\n")
        helper.chmod(0o755)
        state_home = self.work / "state"

        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{tools}:{env['PATH']}",
                "XDG_STATE_HOME": str(state_home),
                "FRANKENSTEIN_BACKGROUND_TEST_MODE": "1",
                "FRANKENSTEIN_BACKGROUND_HELPER": str(helper),
                "FRANKENSTEIN_BACKGROUND_PKEXEC": str(pkexec),
                "EXPECTED_HELPER": str(helper),
                "EXPECTED_INSTALLED": installed,
            }
        )
        result = subprocess.run(
            [IMPORTER], env=env, text=True, capture_output=True, check=True
        )
        evidence_path = state_home / "frankenstein/sddm-state.json"
        evidence = json.loads(evidence_path.read_text())
        self.assertEqual(evidence["schema_version"], 1)
        self.assertEqual(evidence["selected_background"], installed)
        self.assertEqual(evidence["last_known_valid_background"], installed)
        self.assertEqual(
            evidence["default_background"],
            "/usr/share/sddm/themes/frankenstein/backgrounds/vaporwave-default.png",
        )
        self.assertIsNone(evidence["backup_location"])
        self.assertEqual(evidence["detected_sessions"], [])
        self.assertIn("timestamp", evidence["last_validation"])
        self.assertEqual(evidence_path.stat().st_mode & 0o777, 0o600)
        self.assertIn("Evidence updated:", result.stdout)


if __name__ == "__main__":
    unittest.main()
