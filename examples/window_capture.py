#!/usr/bin/env python3
"""Capture screenshots of all visible application windows.

Demonstrates window enumeration and per-window capture via the in-process SDK —
no subprocess, no JSON parsing.

Requirements:
    - Windows 10/11 with a desktop session
    - pip install naturo

Usage:
    python window_capture.py
    python window_capture.py --output-dir ./screenshots
"""

import argparse
import os

import naturo


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture all app windows")
    parser.add_argument("--output-dir", default="screenshots",
                        help="Output directory (default: screenshots)")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    desktop = naturo.Desktop()

    # Enumerate every visible top-level window.
    wins = [w for w in desktop.windows() if w.is_visible and not w.is_minimized]
    print(f"Found {len(wins)} visible window(s)")

    for win in wins:
        # Sanitize the process name into a filename.
        safe_name = "".join(
            c if c.isalnum() or c in "-_ " else "_" for c in win.process_name
        )
        path = os.path.join(args.output_dir, f"{safe_name}_{win.handle}.png")

        print(f"  Capturing {win.process_name}: {win.title[:50]}...")
        try:
            # Target the exact window by its handle — no title guessing.
            result = desktop.capture(path, hwnd=win.handle)
            print(f"    Saved: {result.path} ({result.width}x{result.height})")
        except naturo.NaturoError as exc:
            print(f"    Failed to capture: {exc}")

    print(f"\nScreenshots saved to {args.output_dir}/")


if __name__ == "__main__":
    main()
