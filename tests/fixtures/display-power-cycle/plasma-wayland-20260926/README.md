# KDE Wayland investigation observations

Curated read-only observations from 2026-09-26, following `df07753`.

- `observation.json`: selected package/session/service facts, process-environment
  summary and fields from a successful read-only KScreen query. Omitted raw EDID,
  serials, usernames, process/session IDs, bus address and unrelated settings.
- `history.txt`: selected package/history/journal facts. Not a raw log or a timeline
  of a confirmed TV power-cycle. Event messages retain their originating program.
- `sources.json`: reviewed v6.7.4 source URLs and hashes of downloaded inputs.
  Full sources are retained only in ignored evidence/display-lifecycle-20260926/.
  These hashes support repeat review, not equivalence to the distro build.

No lifecycle operation or recovery request was sent. No TV was power-cycled.
These records are not inputs authorizing adoption or display changes. The older
host-20260926 fixture remains unchanged and documents the original workaround.

See [findings and decision](../../../../docs/DISPLAY-POWER-CYCLE-KDE.md).
