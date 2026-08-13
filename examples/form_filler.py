#!/usr/bin/env python3
"""Drive form-style controls in a Windows application.

Demonstrates key presses, reading the UI tree, and capturing — all via the
in-process SDK. Uses Calculator as a demo target (present on every Windows
system).

Requirements:
    - Windows 10/11 with a desktop session
    - pip install naturo

Usage:
    python form_filler.py
"""

import time

import naturo


def main() -> None:
    # 1. Launch Calculator.
    print("Launching Calculator...")
    with naturo.launch("calculator") as app:
        time.sleep(1)

        # 2. Perform a calculation: 42 * 7 = . Keys are sent to Calculator's
        #    window explicitly, so they land there even if focus drifts.
        print("Entering calculation: 42 * 7 =")
        for key in ("4", "2", "multiply", "7", "enter"):
            app.press(key)
            time.sleep(0.05)

        time.sleep(0.5)

        # 3. Read the result straight from the UI tree — `see` returns the root
        #    Element; walk its descendants for the display text.
        print("Reading result...")
        tree = app.see()
        if tree is not None:
            texts = [
                f'{el.role}: {el.name}'
                for el in tree.descendants()
                if el.role in ("Text", "Edit") and el.name
            ]
            print("Display elements:")
            for line in texts[:10]:
                print(f"  {line}")

        # 4. Capture the result.
        shot = app.capture("calculator_result.png")
        print(f"Screenshot saved to {shot.path}")

        # 5. Leaving the context manager closes Calculator.
        print("Closing Calculator...")

    print("Done!")


if __name__ == "__main__":
    main()
