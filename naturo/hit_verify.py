"""Shared click landing-window hit test and cross-PID verdict (#1207, #1318).

A synthetic coordinate click reaches whatever top-level window sits under the
point — not necessarily the window the caller intended. When the target was
occluded or never came to the foreground, the click silently lands on another
window, yet naturo would still report success (the Never-Lie violation #1207
fixed on the CLI).

Both the CLI ``naturo click`` and the MCP ``click`` tool run the SAME landing
check through this module so their honesty verdict is identical (#1318): report
the window actually under the point, and when a *known* target belongs to a
different process, fail loudly with ``CLICK_WRONG_WINDOW`` instead of claiming a
success that did not happen. The ctypes hit-test helpers and the verdict logic
live here once; each surface binds the helpers as module-local names it can call
(and tests can patch) and shares the pure verdict functions verbatim.
"""
from __future__ import annotations

import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# Raw error-code string emitted on a cross-process landing mismatch. Not an
# ErrorCode enum member — both the CLI (_json_err) and MCP (error envelope)
# surface it by string, and category_for_code degrades unknown codes gracefully.
CLICK_WRONG_WINDOW = "CLICK_WRONG_WINDOW"

# (root_hwnd, window_title, pid) for the top-level window under a screen point.
HitWindow = tuple[int, str, int]


def window_root_at_point(x: int, y: int) -> Optional[HitWindow]:
    """Return the top-level window actually under screen point ``(x, y)``.

    Lets a click command report which window a coordinate click really landed
    on, so naturo never claims success when an overlapping window — or a failed
    foreground switch — silently received the click instead (#1207).

    Args:
        x: Screen X coordinate.
        y: Screen Y coordinate.

    Returns:
        ``(root_hwnd, title, pid)`` for the top-level window at the point, or
        ``None`` if it cannot be determined (e.g. non-Windows or no window).
    """
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.WindowFromPoint.restype = wintypes.HWND
        user32.WindowFromPoint.argtypes = [wintypes.POINT]
        user32.GetAncestor.restype = wintypes.HWND
        user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        hwnd = user32.WindowFromPoint(wintypes.POINT(int(x), int(y)))
        if not hwnd:
            return None
        root = user32.GetAncestor(hwnd, 2) or hwnd  # GA_ROOT = 2
        length = user32.GetWindowTextLengthW(root)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(root, buf, length + 1)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(root, ctypes.byref(pid))
        return int(root), buf.value, int(pid.value)
    except Exception as exc:  # noqa: BLE001 — ctypes/OS errors vary
        logger.debug("WindowFromPoint(%s, %s) failed: %s", x, y, exc)
        return None


def window_pid(hwnd: Optional[int]) -> Optional[int]:
    """Return the process ID owning ``hwnd``, or ``None`` if undeterminable."""
    if sys.platform != "win32" or not hwnd:
        return None
    try:
        import ctypes
        from ctypes import wintypes
        pid = wintypes.DWORD()
        ctypes.windll.user32.GetWindowThreadProcessId(
            wintypes.HWND(int(hwnd)), ctypes.byref(pid)
        )
        return int(pid.value) or None
    except Exception as exc:  # noqa: BLE001 — ctypes/OS errors vary
        logger.debug("GetWindowThreadProcessId(%s) failed: %s", hwnd, exc)
        return None


def hit_window_dict(hit: Optional[HitWindow]) -> Optional[dict]:
    """Serialize a hit tuple into the ``hit_window`` disclosure dict, or ``None``."""
    if not hit:
        return None
    return {"hwnd": hit[0], "title": hit[1], "pid": hit[2]}


def is_cross_pid_mismatch(
    hit: Optional[HitWindow], target_pid: Optional[int]
) -> bool:
    """True when a known target's PID differs from the window under the click.

    Only a *positive* cross-process signal returns True: both the hit window's
    PID and the target PID must be known and differ. An unknown hit, an unknown
    target (bare coordinates), or a same-process landing all return False.
    """
    return bool(hit and target_pid and hit[2] and hit[2] != target_pid)


def wrong_window_message(
    x: Optional[int],
    y: Optional[int],
    hit: HitWindow,
    target_hwnd: Optional[int],
    target_pid: Optional[int],
) -> str:
    """Compose the shared CLICK_WRONG_WINDOW failure message."""
    return (
        f"Click at ({x}, {y}) landed on window {hit[1]!r} "
        f"(hwnd {hit[0]}, pid {hit[2]}), not the target window "
        f"(hwnd {target_hwnd}, pid {target_pid}). The target is "
        f"occluded or failed to come to the foreground; the click did "
        f"not reach it."
    )
