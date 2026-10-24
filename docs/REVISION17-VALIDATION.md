# Revision 17 validation status — 2026-10-24

Revision 17 is an experimental build and installation candidate, not a validated
host upgrade or a certified filtered Plasma shell. The dated source-review
sections in OMARCHY-UPDATES.md describe intermediate checkpoints; this document
records the later build and installation results.

## Changes

- Include KWin in exact compatibility inventories and distinguish reviewed build
  eligibility from runtime validation. Setup, filtered-shell launch and automatic
  recovery remain disabled for the unvalidated target.
- Review the exact Omarchy 4.0.6 shell source contract and the specific Quickshell
  Git package candidate, without accepting arbitrary Git revisions.
- Preserve third-party plugin source-directory metadata while withholding host
  trust markers; qualify Commons.Color in the owned QML forks.
- Build source archives through the repository staging wrapper, accepting an
  explicitly pinned numeric SOURCE_DATE_EPOCH when Git metadata is absent.
- Isolate desktop-routing test fixtures from the executing machine's validation
  status, retaining separate positive and negative production-gate tests.

## Verified evidence

In an offline disposable guest: Omarchy 4.0.6-1, Plasma workspace/KWin 6.8.1-1,
Qt base 6.12.0-3, Qt declarative 6.12.0-2 and Quickshell
0.3.2.r7.g2b4501a-1. All 40 focused Python tests and the bar transformation test
passed. All 59 package source checksums verified. Both split packages compiled
and were exported with matching checksums:

| Package | SHA256 |
| --- | --- |
| frankenstein-core-0.1.0-17-x86_64.pkg.tar.zst | 0ccfd3a5f8f2302f1a0a3ad586a173bdb7c096cb9ea4acfd85a90fafc667cc42 |
| frankenstein-kde-0.1.0-17-x86_64.pkg.tar.zst | 987c06717d48d27d4419239dd97972c8cb17a6d862ee645a4af647b21c1084d1 |

The unsigned local candidates subsequently installed in a disposable guest under
its existing local-package policy, with repository signature checks retained.
Package integrity, scoped integration-preservation comparisons and production
compatibility-gate checks passed. Both stock Hyprland and Plasma sessions were
reached, but the experimental filtered-shell GUI harness was not completed.
Actual built metadata resolves a coordinated full-update dependency plan; solver
success does not establish file-conflict, migration or runtime safety.

## Not established

No new validated_stacks entry was added. Custom bar/menu/settings/wallpaper
behavior, real installer rollback, the complete managed Omarchy migration path
and host boot recovery remain unverified. No host update or production release
was performed. Do not deploy these artifacts merely to clear version pins or
install the Qt 6.12-built KDE module alone onto an older desktop stack.

The guest-only test instrumentation and temporary greeter adjustment are not
part of the shipped source. VM images, private logs and machine configuration
are excluded from this repository change.
