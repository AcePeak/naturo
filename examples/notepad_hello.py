#!/usr/bin/env python3
"""Open Notepad, type a greeting, and close it.

Demonstrates the full app lifecycle with the ergonomic in-process SDK:
launch -> interact -> capture -> quit. No subprocess, no CLI parsing — just
``import naturo``.

Requirements:
    - Windows 10/11 with a desktop session
    - pip install naturo

Usage:
    python notepad_hello.py
"""

import time

import naturo


def main() -> None:
    # 1. Launch Notepad — `launch` waits until its window is ready and returns
    #    an App handle usable as a context manager (quits on exit).
    print("Launching Notepad...")
    with naturo.launch("notepad") as app:
        time.sleep(0.5)

        # 2. Type a greeting into Notepad's window. `type` routes through the
        #    IME-immune ladder (ValuePattern -> clipboard -> keystroke), so it
        #    stays correct even on CJK/TSF input hosts.
        print("Typing text...")
        app.type("Hello from naturo!")
        app.press("enter")
        app.type("This text was typed by an automation script.")

        # 3. Capture a screenshot to verify.
        print("Capturing screenshot...")
        shot = app.capture("notepad_result.png")
        print(f"Screenshot saved to {shot.path} ({shot.width}x{shot.height})")

        # 4. Leaving the `with` block quits Notepad. Notepad may raise a
        #    "Save?" dialog; dismiss it so the app really closes.
        print("Closing Notepad...")

    time.sleep(0.5)
    try:
        naturo.press("alt+n")  # "Don't Save" accelerator on Win11 Notepad
    except naturo.NaturoError:
        pass  # No dialog — already closed

    print("Done!")


if __name__ == "__main__":
    main()
