"""Minimal `naturo run` example — count open windows via the naturo SDK.

Run it with::

    naturo run examples/scripts/hello_windows.py

The script imports the #924 in-process SDK and calls ``windows()``, which only
*enumerates* the open top-level windows — it drives no input, so it is safe to
run on a live desktop.
"""
from __future__ import annotations

from naturo import windows


def main() -> None:
    """Print how many top-level windows are currently open."""
    open_windows = windows()
    print("OK", len(open_windows))


if __name__ == "__main__":
    main()
