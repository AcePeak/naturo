#!/usr/bin/env python3
"""Open Notepad, type a greeting, and close it.

Demonstrates the full app lifecycle: launch → interact → quit.

Requirements:
    - Windows 10/11 with a desktop session
    - pip install naturo

Usage:
    python notepad_hello.py
"""

import subprocess
import sys
import time


def run(cmd: str) -> str:
    """Run a naturo CLI command and return stdout."""
    result = subprocess.run(
        ["naturo"] + cmd.split(),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Command failed: naturo {cmd}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def main() -> None:
    # 1. Launch Notepad and wait for its window
    print("Launching Notepad...")
    run("app launch notepad --wait-until-ready")
    time.sleep(0.5)

    # 2. Type a greeting
    print("Typing text...")
    run("type Hello from naturo!")
    run("press enter")
    run("type This text was typed by an automation script.")

    # 3. Take a screenshot to verify
    print("Capturing screenshot...")
    run("capture --app notepad --path notepad_result.png")
    print("Screenshot saved to notepad_result.png")

    # 4. Close without saving — dismiss the save dialog
    print("Closing Notepad...")
    run("app quit notepad")

    # If a "Save?" dialog appears, dismiss it
    time.sleep(0.5)
    try:
        run("dialog dismiss --app notepad")
    except SystemExit:
        pass  # No dialog — already closed

    print("Done!")


if __name__ == "__main__":
    main()
