#!/usr/bin/env python3
"""Capture screenshots of all visible application windows.

Demonstrates window enumeration and per-app screenshot capture.

Requirements:
    - Windows 10/11 with a desktop session
    - pip install naturo

Usage:
    python window_capture.py
    python window_capture.py --output-dir ./screenshots
"""

import argparse
import json
import os
import subprocess
import sys


def run_json(cmd: str) -> dict:
    """Run a naturo CLI command with --json and parse the output."""
    result = subprocess.run(
        ["naturo"] + cmd.split() + ["--json"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Command failed: naturo {cmd} --json", file=sys.stderr)
        return {"success": False}
    return json.loads(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture all app windows")
    parser.add_argument("--output-dir", default="screenshots",
                        help="Output directory (default: screenshots)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # List all visible application windows
    data = run_json("app list")
    if not data.get("success"):
        print("Failed to list applications.", file=sys.stderr)
        sys.exit(1)

    apps = data.get("apps", [])
    print(f"Found {len(apps)} application(s)")

    for app in apps:
        app_id = app.get("id", "")
        title = app.get("title", "unknown")
        process = app.get("process_name", "unknown")

        # Sanitize filename
        safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in process)
        path = os.path.join(args.output_dir, f"{safe_name}_{app_id}.png")

        print(f"  Capturing {process}: {title[:50]}...")
        result = subprocess.run(
            ["naturo", "capture", "--hwnd", str(app.get("handle", 0)),
             "--path", path],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"    Saved: {path}")
        else:
            print("    Failed to capture")

    print(f"\nScreenshots saved to {args.output_dir}/")


if __name__ == "__main__":
    main()
