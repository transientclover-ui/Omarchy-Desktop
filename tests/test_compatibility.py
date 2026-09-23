import contextlib
import io
import unittest
from unittest.mock import patch

from omarchy_desktop.cli import main
from omarchy_desktop.compatibility import compatibility
from omarchy_desktop.discovery import DESKTOPS
from omarchy_desktop.prompts import generate


class CompatibilityTests(unittest.TestCase):
    def test_no_unsupported_certifications(self):
        for desktop in DESKTOPS:
            self.assertEqual(compatibility(desktop, "unknown")["status"], "not verified")

    def test_unverified_install_and_switch_are_inspection_only(self):
        for desktop in DESKTOPS:
            for action in ("install", "switch"):
                prompt = generate(action, desktop, {"omarchy_version": "unknown"})
                self.assertIn("DEFERRED", prompt)
                self.assertIn("Do not install, switch or change", prompt)

    def test_evidence_is_version_specific(self):
        with patch.dict("omarchy_desktop.compatibility.VERIFIED", {("kde", "test-version"): "test-report.md"}):
            self.assertEqual(compatibility("kde", "test-version")["status"], "tested")
            self.assertEqual(compatibility("kde", "another-version")["status"], "not verified")
            prompt = generate("install", "kde", {"omarchy_version": "test-version"})
            self.assertIn("INSTALL PLAN", prompt)
            self.assertIn("test-report.md", prompt)
            self.assertIn("explicit confirmation and WAIT", prompt)
            self.assertIn("check every constraint", prompt)

    def test_shell_default_applies_even_to_repair(self):
        for action in ("inspect", "verify", "install", "switch", "recover", "repair-sddm"):
            prompt = generate(action, "kde", {"omarchy_version": "unknown"})
            self.assertIn("Omarchy shell must be enabled by default", prompt)
            self.assertIn("choose to disable it later", prompt)

    def test_new_commands(self):
        for args in (["compatibility"], ["verify", "budgie"]):
            with patch("omarchy_desktop.cli.discover", return_value={"omarchy_version": "unknown"}), contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(main(args), 0)
            self.assertTrue(out.getvalue())


class LoginRegressionTests(unittest.TestCase):
    def test_repair_identifies_both_login_screens(self):
        prompt = generate("repair-sddm", None, {"omarchy_version": "unknown"})
        self.assertIn("SDDM login -> another login -> desktop", prompt)
        self.assertIn("identify the owner of each screen", prompt)
        self.assertIn("working explicit and idle locking", prompt)
