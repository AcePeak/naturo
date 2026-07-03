"""Rival adapters — each recognizes the UI of a window and returns a count of
elements it can actually see. Same input (an HWND), comparable output.

- **naturo**: the unified cascade (UIA + JAB + COM + CDP), counting nodes by the
  technique that recognized them — so Java/COM/web content shows up.
- **pywinauto (uia)**: its UIA element tree (``descendants()``). UIA collapses
  Java/COM/web internals into opaque nodes, so it recognizes only the chrome.
- **PyAutoGUI**: pixels only — no element model at all (structural recognition = 0).
"""
from __future__ import annotations

from typing import Any


def naturo_recognize(hwnd: int) -> dict[str, Any]:
    """naturo unified cascade → total nodes + per-technique breakdown."""
    from collections import Counter
    from naturo.backends.base import get_backend
    from naturo.cascade import run_cascade

    backend = get_backend()
    res = run_cascade(backend, hwnd=hwnd, depth=12, backend_name="auto")
    by = Counter()

    def _walk(node):
        if node is None:
            return
        src = (getattr(node, "properties", None) or {}).get("source")
        by[src] += 1
        for child in (getattr(node, "children", None) or []):
            _walk(child)

    _walk(res.tree)
    return {"elements": sum(by.values()), "by_technique": dict(by)}


def pywinauto_recognize(hwnd: int) -> dict[str, Any]:
    """pywinauto's UIA descendant count for the window."""
    from pywinauto import Desktop  # comtypes gen must be prepared first
    win = Desktop(backend="uia").window(handle=hwnd)
    return {"elements": len(win.descendants())}


def pyautogui_recognize(hwnd: int) -> dict[str, Any]:
    """PyAutoGUI has no element model — structural recognition is always 0."""
    import pyautogui  # noqa: F401  (import proves it is installed/runnable)
    return {"elements": 0, "note": "no element model (pixels only)"}


RIVALS = {
    "naturo": naturo_recognize,
    "pywinauto": pywinauto_recognize,
    "pyautogui": pyautogui_recognize,
}
