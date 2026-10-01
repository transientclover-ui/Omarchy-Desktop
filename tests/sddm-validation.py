#!/usr/bin/env python3
"""Regression tests for fail-closed SDDM theme activation validation."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
VALIDATOR = PROJECT / "src/libexec/frankenstein-sddm-validate"
THEME = PROJECT / "src/sddm/frankenstein"


class SddmValidationTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix=".sddm-validation.", dir=PROJECT / "tests"))
        self.addCleanup(shutil.rmtree, self.work, ignore_errors=True)
        self.root = self.work / "root"
        self.theme = self.root / "usr/share/sddm/themes/frankenstein"
        shutil.copytree(THEME, self.theme)
        (self.root / "usr/bin").mkdir(parents=True)
        greeter = self.root / "usr/bin/sddm-greeter-qt6"
        greeter.write_text("#!/bin/sh\nexit 0\n")
        greeter.chmod(0o755)
        scanner = self.root / "usr/lib/qt6/qmlimportscanner"
        scanner.parent.mkdir(parents=True)
        scanner.write_text(
            "#!/bin/sh\n"
            "printf '%s\\n' '[{\"name\":\"QtQuick\",\"type\":\"module\"},"
            "{\"name\":\"QtQuick.Controls\",\"type\":\"module\"},"
            "{\"name\":\"QtQuick.Layouts\",\"type\":\"module\"},"
            "{\"name\":\"Qt.labs.settings\",\"type\":\"module\"}]'\n"
        )
        scanner.chmod(0o755)
        for module in (
            "QtQuick",
            "QtQuick/Controls",
            "QtQuick/Layouts",
            "Qt/labs/settings",
        ):
            path = self.root / "usr/lib/qt6/qml" / module
            path.mkdir(parents=True)
            (path / "qmldir").write_text("module " + module.replace("/", ".") + "\n")
        tools = self.work / "tools"
        tools.mkdir()
        for name, body in {
            "ldd": "#!/bin/sh\nexit 0\n",
            "jq": shutil.which("jq"),
            "awk": shutil.which("awk"),
            "sed": shutil.which("sed"),
            "tr": shutil.which("tr"),
            "sort": shutil.which("sort"),
        }.items():
            path = tools / name
            if body and body.startswith("/"):
                path.symlink_to(body)
            else:
                path.write_text(body)
                path.chmod(0o755)
        self.env = dict(
            os.environ,
            PATH=f"{tools}:{os.environ['PATH']}",
        )

    def run_validator(self):
        return subprocess.run(
            [
                VALIDATOR,
                self.theme,
                self.root / "usr/bin/sddm-greeter-qt6",
                self.root / "usr/lib/qt6/qmlimportscanner",
                self.root / "usr/lib/qt6/qml",
            ],
            env=self.env,
            text=True,
            capture_output=True,
            timeout=5,
        )

    def test_complete_qt6_theme_passes(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_asset_fails_closed(self):
        (self.theme / "backgrounds/vaporwave-default.png").unlink()
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("required theme file", result.stderr)

    def test_missing_qml_module_fails_closed(self):
        shutil.rmtree(self.root / "usr/lib/qt6/qml/QtQuick/Controls")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("QtQuick.Controls", result.stderr)

    def test_missing_qt_version_fails_before_qml(self):
        metadata = self.theme / "metadata.desktop"
        metadata.write_text(metadata.read_text().replace("QtVersion=6\n", ""))
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("QtVersion=6", result.stderr)


if __name__ == "__main__":
    unittest.main()
