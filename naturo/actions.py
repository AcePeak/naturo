"""Shared input-action helpers used by BOTH the CLI and MCP surfaces.

Keeping the ``type`` reliability ladder in one place is what stops the two
surfaces from drifting apart the way #1219 exposed: MCP ``type_text`` already
climbed the ValuePattern -> clipboard -> keystroke ladder (each rung IME-immune
until the last), but the CLI ``naturo type`` called the raw keystroke backend
directly, so it corrupted text on CJK/TSF IME hosts ("naturo" -> "nature",
"quick" -> "cccck"). Both surfaces now route through :func:`smart_type_text`,
so the honest, IME-immune path can never regress on one surface alone.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def paste_text(backend, text: str, *, restore: bool = True) -> bool:
    """Insert ``text`` via clipboard paste — atomic, fast, and IME-immune.

    A fast per-character SendInput drops characters on heavy controls (Win11
    Notepad's RichEdit under the modern TSF input host): "hello from naturo"
    lands as "hello      turo". Pasting inserts the whole string in one shot,
    so there is no per-key race and no IME composition to corrupt it. When
    ``restore`` is set (the default) the caller's prior clipboard is saved and
    restored so it is not clobbered.

    Returns True if the paste was delivered (clipboard set + Ctrl+V sent).

    (#1160) The clipboard content is routed through the SAME NATURO_SAFE_INPUT
    guard as keystroke typing before Ctrl+V: pasting is subject to the identical
    SendInput/focus-race threat, so a bare paste must not become a bypass. When
    the guard is armed and ``text`` is unsafe, nothing is set on the clipboard
    and nothing is pasted — the helper returns False without delivering.
    """
    from naturo.safety import unsafe_input_reason
    if unsafe_input_reason(text):
        return False
    saved = None
    if restore:
        try:
            saved = backend.clipboard_get()
        except Exception:
            saved = None
    delivered = False
    try:
        backend.clipboard_set(text)
        backend.hotkey("ctrl", "v")
        time.sleep(0.06)  # let the target consume the clipboard before restoring it
        delivered = True
    except Exception:
        delivered = False
    if restore and saved is not None:
        try:
            backend.clipboard_set(saved)
        except Exception:
            pass
    return delivered


def smart_type_text(
    backend,
    text: str,
    *,
    input_mode: str = "normal",
    wpm: int = 120,
    delay_ms: Optional[int] = None,
    profile: str = "human",
    append: bool = True,
    restore: bool = True,
) -> str:
    """Type ``text`` via the IME-immune reliability ladder; return the method.

    (#1219) Keystroke injection (SendInput) is intercepted by CJK/TSF IMEs and
    can corrupt text ("naturo" -> "nature"). Prefer a non-keystroke path.

    Reliability ladder — each rung is exact; fall to the next only if it can't
    apply:

      1. ``value_pattern``: the focused control exposes a writable UIA
         ValuePattern -> set its value directly (instant, no keyboard,
         inherently IME-immune);
      2. ``clipboard_paste``: clipboard + Ctrl+V -> insert atomically (fast,
         IME-immune, no per-key race) — what heavy TSF controls like Win11
         Notepad need (fast keystroke SendInput drops chars there);
      3. ``keystroke``: SendInput at the requested speed — the last resort, and
         the only IME-vulnerable rung.

    Only ``input_mode == "normal"`` climbs the ladder. ``"hardware"`` / ``"hook"``
    are explicit raw-injection escape hatches and go straight to the keystroke
    rung. Returns the method string of the rung that delivered the text
    (``"value_pattern"`` | ``"clipboard_paste"`` | ``"keystroke"``).
    """
    method = "keystroke"
    used = False
    # (#563) UIA ValuePattern.SetValue collapses newlines, so multiline text
    # must skip the value_pattern rung and go to clipboard (which preserves
    # them). Single-line text still prefers the instant ValuePattern path.
    has_newline = ("\n" in text) or ("\r" in text)
    if input_mode == "normal" and not has_newline:
        used = bool(backend.set_focused_element_value(text, append=append))
        if used:
            method = "value_pattern"
    if not used and input_mode == "normal" and paste_text(backend, text, restore=restore):
        used = True
        method = "clipboard_paste"
    if not used:
        kwargs: dict = {"wpm": wpm, "input_mode": input_mode, "profile": profile}
        if delay_ms is not None:
            kwargs["delay_ms"] = delay_ms
        backend.type_text(text, **kwargs)
    return method
