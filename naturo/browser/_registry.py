"""Process-local map of a browser window handle to its CDP debug port.

``launch_browser`` records the port it opened a window on; ``read_web_text``
(and other CDP readers) look it up to attach to the *exact* instance behind a
given hwnd, instead of blind-probing the common ports — which returns the wrong
browser when more than one debuggable browser is alive (CDP cross-talk).

The map lives for the life of the MCP server process. Both ends of the common
flow (launch_browser -> read_web_text) run in that same process, so a lookup by
hwnd is exact even when a stray debuggable browser from elsewhere is running.
"""
from __future__ import annotations

from typing import Optional

_HWND_PORT: dict[int, int] = {}


def record(hwnd: Optional[int], port: Optional[int]) -> None:
    """Remember that window ``hwnd`` exposes CDP on ``port``."""
    if hwnd is not None and port:
        _HWND_PORT[int(hwnd)] = int(port)


def lookup(hwnd: Optional[int]) -> Optional[int]:
    """Return the recorded CDP port for ``hwnd``, or None if unknown."""
    if hwnd is None:
        return None
    return _HWND_PORT.get(int(hwnd))


def forget(hwnd: Optional[int]) -> None:
    """Drop ``hwnd`` from the map (e.g. after the window closes)."""
    if hwnd is not None:
        _HWND_PORT.pop(int(hwnd), None)
