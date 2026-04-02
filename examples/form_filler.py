#!/usr/bin/env python3
"""Auto-fill form fields in a Windows application.

Demonstrates element discovery, clicking, and typing into form controls.
Uses Calculator as a demo target (available on all Windows systems).

Requirements:
    - Windows 10/11 with a desktop session
    - pip install naturo

Usage:
    python form_filler.py
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
    return result.stdout.strip()


def main() -> None:
    # 1. Launch Calculator
    print("Launching Calculator...")
    run("app launch calculator --wait-until-ready")
    time.sleep(1)

    # 2. Perform a calculation: 42 * 7 =
    print("Entering calculation: 42 * 7 =")

    # Type digits and operators using keyboard
    run("press 4")
    run("press 2")
    run("press multiply")  # * key
    run("press 7")
    run("press enter")     # = key

    time.sleep(0.5)

    # 3. Read the result from the display
    print("Reading result...")
    output = run("see --app calculator --json")
    print(f"Calculator output: {output[:200]}...")

    # 4. Take a screenshot of the result
    run("capture --app calculator --path calculator_result.png")
    print("Screenshot saved to calculator_result.png")

    # 5. Close Calculator
    print("Closing Calculator...")
    run("app quit calculator")
    print("Done!")


if __name__ == "__main__":
    main()
