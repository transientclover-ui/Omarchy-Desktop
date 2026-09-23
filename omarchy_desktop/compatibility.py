"""Evidence-based Omarchy shell compatibility, independent of session detection."""
# (desktop, exact Omarchy version) -> reviewed repository test report.
# Populate only after actual graphical integration testing; CLI tests do not count.
VERIFIED = {}


def compatibility(desktop, version):
    report = VERIFIED.get((desktop, version))
    return {"status": "tested" if report else "not verified", "report": report,
            "omarchy_version": version}


SHELL_CHECKS = """Omarchy shell must be enabled by default in the proposed setup. Preserve its
configuration and arrange session-appropriate startup only after approval. Do not
disable it to make another desktop appear compatible. The user may explicitly
choose to disable it later in a separate task. Prevent duplicate instances without
blindly disabling services. Existing approval and inspection-only rules still apply.
Compatibility means the Omarchy shell experience, not merely a successful login.
Record exact Omarchy version/commit, shell modifications, desktop/compositor,
Quickshell, SDDM, session type, graphics driver, hardware/VM and test date.
Read and check every constraint in any cited compatibility report; a matching
Omarchy version alone does not establish matching hardware or configuration.
Perform graphical tests only in a separately approved disposable VM or dedicated
test system, never by changing the user's working desktop. Check shell startup
and restart; bar/launcher; workspaces/window controls; notifications/tray;
audio/network/Bluetooth; themes; shortcuts/clipboard; dialogs/screen sharing;
polkit; lock/unlock; idle/suspend/resume; monitors/scaling; logout/login;
SDDM selection of another desktop and back (including stuck-last-session behavior);
and recovery. Record pass/fail/blocked with reproducible evidence for every check.
A screenshot, running process or passing CLI tests is insufficient. Document
native replacements and hardware exclusions; do not silently count a replacement
for Omarchy shell functionality as full compatibility. Failed or untested required
features prevent certification. Never manufacture test evidence.
"""
