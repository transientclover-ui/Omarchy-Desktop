"""Beginner-friendly CLI; stdout only, no mutating system operations."""
import argparse
import json
import sys
from . import __version__
from .discovery import DESKTOPS, discover
from .prompts import generate


def safe(value):
    return str(value).encode("unicode_escape").decode("ascii")


def show(report):
    print("Omarchy Desktop — read-only discovery")
    print(f"Omarchy: {safe(report['omarchy_version'])} | Current desktop: {safe(report['current_desktop'])}")
    print(f"Login manager link: {safe(report['display_manager_link'])}")
    print("\nChoose a desktop (detected entries do not guarantee a working login):")
    for key, (label, _) in DESKTOPS.items():
        matches = [s for s in report["sessions"] if s["desktop"] == key]
        status = "; ".join(f"{safe(s['id'])}: {s['status']}" for s in matches) or "no entry detected"
        print(f"  {key:10} {label:15} {status}")
    others = [s for s in report["sessions"] if s["desktop"] == "other"]
    for session in others:
        print(f"  Other: {safe(session['name'])} ({safe(session['path'])})")
    for finding in report["sddm_findings"]:
        print(f"\nSDDM: {safe(finding['detail'])}")
    for warning in report["warnings"]:
        print(f"Warning: {safe(warning)}")
    print("\nNext: omarchy-desktop inspect kde   |   omarchy-desktop repair-sddm")
    print("All commands only print information or prompts. No desktop changes are made.")


def choose(report):
    show(report)
    if not sys.stdin.isatty():
        print("\nFor the guided menu, run in a terminal. Otherwise choose a command with --help.")
        return
    print("\nType a desktop key, 'sddm' for login repair, or 'q' to quit.")
    desktop = input("Your choice: ").strip().lower()
    if desktop in ("q", ""):
        return
    if desktop == "sddm":
        action, desktop = "repair-sddm", None
    else:
        if desktop not in DESKTOPS:
            print("Unknown desktop. Run again and choose a listed key.")
            return
        print("Choose: inspect (look first), install, switch, recover")
        action = input("Task [inspect]: ").strip().lower() or "inspect"
        if action not in ("inspect", "install", "switch", "recover"):
            print("Unknown task. No changes made.")
            return
    print("\nCopy the following prompt to your preferred AI agent. Review the local evidence first.\n")
    print(generate(action, desktop, report))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Choose a desktop and prepare a safe AI task. Never installs or switches anything itself.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--root", default="/", help="inspect a filesystem fixture instead of the live system (before command)")
    sub = parser.add_subparsers(dest="command")
    for name in ("list", "doctor"):
        child = sub.add_parser(name, help="read-only desktop and SDDM evidence")
        child.add_argument("--json", action="store_true", help="print structured evidence")
    sub.add_parser("choose", help="guided desktop/task menu")
    for name in ("inspect", "install", "switch", "recover"):
        child = sub.add_parser(name, help=f"print an AI {name} prompt; makes no changes")
        child.add_argument("desktop", choices=DESKTOPS)
    sub.add_parser("repair-sddm", help="print a diagnosis and approval-gated SDDM repair prompt")
    args = parser.parse_args(argv)
    try:
        report = discover(args.root)
        if args.command in (None, "choose"):
            choose(report)
        elif args.command in ("list", "doctor"):
            if args.json:
                print(json.dumps(report, indent=2, ensure_ascii=True))
            else:
                show(report)
                if args.command == "doctor":
                    print("\nDetails (review before sharing):\n" + json.dumps(report, indent=2, ensure_ascii=True))
        else:
            print(generate(args.command, getattr(args, "desktop", None), report))
        return 0
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. No system changes made.", file=sys.stderr)
        return 130
    except BrokenPipeError:
        return 0
