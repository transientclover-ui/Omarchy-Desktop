#!/usr/bin/env python3
"""Tests for full-update-first Frankenstein package installation."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
INSTALLER = PROJECT / "install-frankenstein.sh"


class InstallWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix=".install-workflow.", dir=PROJECT / "tests"))
        self.addCleanup(shutil.rmtree, self.work, ignore_errors=True)
        self.tools = self.work / "tools"
        self.tools.mkdir()
        self.log = self.work / "operations.log"
        self.modules = self.work / "modules"
        (self.modules / "test-kernel").mkdir(parents=True)
        self.reboot_marker = self.work / "reboot-required"
        self.core = self.work / "frankenstein-core.pkg.tar.zst"
        self.kde = self.work / "frankenstein-kde.pkg.tar.zst"
        self.core.write_bytes(b"core")
        self.kde.write_bytes(b"kde")
        self.stage_installer()
        self.write_tool(
            "pacman",
            """case "$1" in
-Qp)
  case "$3" in
    *frankenstein-core*) echo 'frankenstein-core 0.1.0-10';;
    *frankenstein-kde*) echo 'frankenstein-kde 0.1.0-10';;
    *) exit 2;;
  esac;;
-U) printf 'pacman %s\\n' "$*" >>"$OPERATION_LOG";;
*) exit 3;;
esac
""",
        )
        self.write_tool(
            "omarchy",
            """printf 'omarchy %s\\n' "$*" >>"$OPERATION_LOG"
[[ ${ADVISE_UPDATE:-0} == 0 ]] || : >"$FRANKENSTEIN_UPDATE_ADVISORY"
[[ ${FAIL_UPDATE:-0} == 0 ]]
""",
        )
        self.write_tool("sudo", 'exec "$@"\n')
        self.write_tool(
            "frankenstein",
            """printf 'frankenstein %s\\n' "$*" >>"$OPERATION_LOG"\n""",
        )
        self.write_tool("uname", "echo test-kernel\n")

    def stage_installer(self):
        text = INSTALLER.read_text()
        text = text.replace("/run/reboot-required", str(self.reboot_marker))
        text = text.replace("/usr/lib/modules", str(self.modules))
        text = text.replace(
            "command -v frankenstein >/dev/null 2>&1",
            f"[[ -x {self.tools / 'frankenstein'} ]]",
        )
        self.installer = self.work / "install-frankenstein.sh"
        self.installer.write_text(text)
        self.installer.chmod(0o755)
        guard = self.work / "src/update-safety-bin/omarchy-update-restart"
        guard.parent.mkdir(parents=True)
        shutil.copy2(
            PROJECT / "src/update-safety-bin/omarchy-update-restart", guard
        )

    def write_tool(self, name, body):
        path = self.tools / name
        path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + body)
        path.chmod(0o755)

    def run_installer(self, *, fail_update=False, advise_update=False):
        env = dict(
            os.environ,
            PATH=f"{self.tools}:{os.environ['PATH']}",
            OPERATION_LOG=str(self.log),
            FAIL_UPDATE="1" if fail_update else "0",
            ADVISE_UPDATE="1" if advise_update else "0",
        )
        return subprocess.run(
            [
                self.installer,
                self.core,
                self.kde,
                "--",
                "--login",
                "frankenstein",
            ],
            env=env,
            text=True,
            capture_output=True,
            timeout=10,
        )

    def operations(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_update_precedes_package_and_configuration_install(self):
        result = self.run_installer()
        self.assertEqual(result.returncode, 0, result.stderr)
        operations = self.operations()
        self.assertEqual(operations[0], "omarchy update -y")
        self.assertTrue(operations[1].startswith("pacman -U --needed -- "))
        self.assertEqual(
            operations[2], "frankenstein install --login frankenstein"
        )
        self.assertNotIn("-Sy", operations[1])
        self.assertFalse(
            any("reboot" in operation or "systemctl" in operation for operation in operations)
        )

    def test_fresh_install_does_not_require_frankenstein_command_before_packages(self):
        (self.tools / "frankenstein").unlink()
        result = self.run_installer()
        self.assertNotEqual(result.returncode, 0)
        operations = self.operations()
        self.assertEqual(operations[0], "omarchy update -y")
        self.assertTrue(operations[1].startswith("pacman -U --needed -- "))
        self.assertIn(
            "Frankenstein command is missing after package installation",
            result.stderr,
        )

    def test_update_failure_aborts_before_any_installation(self):
        result = self.run_installer(fail_update=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.operations(), ["omarchy update -y"])
        self.assertIn("packages and configuration were not installed", result.stderr)

    def test_reboot_advisory_stops_before_any_installation(self):
        result = self.run_installer(advise_update=True)
        self.assertEqual(result.returncode, 75)
        self.assertEqual(self.operations(), ["omarchy update -y"])
        self.assertIn("reboot is advisable", result.stderr)

    def test_external_reboot_marker_stops_before_any_installation(self):
        self.reboot_marker.write_text("reboot\n")
        result = self.run_installer()
        self.assertEqual(result.returncode, 75)
        self.assertEqual(self.operations(), ["omarchy update -y"])

    def test_update_finalizer_contains_no_restart_command(self):
        finalizer = (
            PROJECT / "src/update-safety-bin/omarchy-update-restart"
        ).read_text()
        for forbidden in (
            "omarchy-system-reboot",
            "omarchy-restart-",
            "systemctl",
            "shutdown",
        ):
            self.assertNotIn(forbidden, finalizer)


if __name__ == "__main__":
    unittest.main()
