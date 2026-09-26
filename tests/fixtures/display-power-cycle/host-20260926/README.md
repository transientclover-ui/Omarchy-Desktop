# Retained TV workaround evidence

These files are evidence, **not installable configuration**. They are intentionally
stored as non-executable `.txt` files and excluded from package/install payloads.

- `recover-tv-display.sh.txt` and `recover-tv-display.service.txt` were read directly
  from the host on 2026-09-26. Only `/home/violet` was replaced with `/home/test`.
- `user-copy.rules.txt` is the directly read copy under the user's .config/udev,
  including its malformed `ENV DBUS_SESSION_BUS_ADDRESS` line. It is not evidence
  of the active system rule's syntax.
- `active-rule.user-supplied.txt` preserves the rule excerpt supplied by the user
  after root-only permissions prevented direct reading. The same home redaction
  applies; terminal prompt and trailing empty line were omitted. The pasted first
  line lacks `#`; this is recorded rather than silently repaired or claimed to be
  an actual active-file parse error. Exact active-file bytes/mode were not copied.
- `observation.json` is a curated record of read-only host checks and historical
  journal findings, not a full machine inventory or an authoritative health report.

No credentials, EDID bytes, hardware serial numbers, unrelated settings or raw
journal exports are retained. The UID/connector assumptions are part of the
workaround and remain visible. Host service status is time-specific.

Run `PYTHONDONTWRITEBYTECODE=1 python3 -W error tests/display-power-cycle-evidence.py`.
Tests change only the connector path in a temporary copy of the script, to a
regular fixture directory. External commands resolve through a closed temporary
PATH containing selected file utilities and harmless stubs. No real systemctl,
DBus or KScreen command is invoked; writable power_mode in one case is a temporary
regular file. These tests reproduce limitations, not successful HDMI recovery.

See [investigation and remaining integration work](../../../../docs/DISPLAY-POWER-CYCLE.md).
