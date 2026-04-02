#!/usr/bin/env python3
"""Interactive UI tree exploration for a target application.

Lists the UI element tree, lets you inspect elements by reference,
and demonstrates the see → find → click workflow.

Requirements:
    - Windows 10/11 with a desktop session
    - pip install naturo

Usage:
    python ui_inspector.py notepad
    python ui_inspector.py calculator --depth 3
"""

import argparse
import json
import subprocess
import sys


def run(cmd: str) -> str:
    """Run a naturo CLI command and return stdout."""
    result = subprocess.run(
        ["naturo"] + cmd.split(),
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def run_json(cmd: str) -> dict:
    """Run a naturo CLI command with --json and parse the output."""
    result = subprocess.run(
        ["naturo"] + cmd.split() + ["--json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return {"success": False, "error": result.stderr.strip()}
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore UI element tree")
    parser.add_argument("app", help="Application name (e.g. notepad, calculator)")
    parser.add_argument("--depth", type=int, default=5,
                        help="Maximum tree depth to display (default: 5)")
    args = parser.parse_args()

    print(f"Inspecting UI tree for '{args.app}'...\n")

    # Get the UI element tree
    data = run_json(f"see --app {args.app} --depth {args.depth}")
    if not data.get("success"):
        print(f"Failed to inspect {args.app}. Is it running?", file=sys.stderr)
        sys.exit(1)

    elements = data.get("elements", [])
    print(f"Found {len(elements)} UI elements:\n")

    for elem in elements:
        ref = elem.get("ref", "")
        role = elem.get("role", "")
        name = elem.get("name", "")
        indent = "  " * elem.get("depth", 0)
        print(f"{indent}{ref:>4}  [{role}]  {name}")

    # Interactive exploration loop
    print("\n--- Interactive Mode ---")
    print("Enter an element ref (e.g. e1) to inspect, or 'q' to quit.\n")

    while True:
        try:
            ref = input("Inspect ref> ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if ref.lower() in ("q", "quit", "exit"):
            break

        if not ref:
            continue

        info = run_json(f"find --on {ref} --app {args.app}")
        if info.get("success"):
            elem = info.get("element", info)
            print(json.dumps(elem, indent=2))
        else:
            print(f"Element {ref} not found.")

    print("Done.")


if __name__ == "__main__":
    main()
