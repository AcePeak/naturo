"""Shared high-level action orchestration used by BOTH the CLI and the MCP surface.

The CLI commands (``naturo/cli/**``) and the MCP tools (``naturo/mcp/**``) are two
thin wrappers over the same backend. When each wrapper re-implements a reliability
ladder independently they drift — and the drift is silent. The concrete bug that
motivated this module: the MCP ``type_text`` pasted via Ctrl+V *before* trying
keystrokes and *without verifying* the paste landed, while the CLI ``type`` typed
first and only fell back to paste after a *verified* failure. On a CEF/Chromium
control (DingTalk) that silently drops a synthetic Ctrl+V, the MCP path reported
success while nothing was entered; the CLI path worked. Same engine, divergent
wrappers.

Put the ladders here once. Both surfaces call the same function, so they cannot
drift again.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


# Modifier keys that can be pressed standalone (Alt activates the menu bar, etc.).
# The bridge's key_press() only handles regular named keys, so a bare modifier
# must be routed through hotkey() with a modifier-only flag. Shared here so the
# CLI `press` and MCP `press_key` surfaces resolve them identically.
_MODIFIER_ALIASES: dict[str, str] = {
    "alt": "alt", "lalt": "alt", "ralt": "alt",
    "ctrl": "ctrl", "control": "ctrl", "lctrl": "ctrl", "rctrl": "ctrl",
    "shift": "shift", "lshift": "shift", "rshift": "shift",
    "win": "win", "meta": "win", "super": "win",
    "command": "win", "cmd": "win", "lwin": "win", "rwin": "win",
}


def is_standalone_modifier(key: str) -> bool:
    """True if *key* is a lone modifier (alt/ctrl/shift/win, incl. aliases)."""
    return key.lower().strip() in _MODIFIER_ALIASES


def smart_press_key(
    backend, key: str, *, count: int = 1, input_mode: str = "normal"
) -> dict:
    """Press *key* (or a '+'-combo) *count* times, shared by CLI + MCP.

    A '+'-combo (``ctrl+c``) or a lone modifier (``alt``) routes through
    ``hotkey()`` — the bridge's ``key_press`` cannot hold a bare modifier down —
    while every other key goes through ``press_key()``. Centralising this here
    stops the MCP ``press_key`` (which used to send a lone ``alt`` straight to
    ``press_key`` and no-op) from drifting from the CLI, which special-cases it.

    Returns ``{"method": "hotkey"|"key", "combo": <str|None>}``.
    """
    combo = "+" in key
    modifier = is_standalone_modifier(key)
    for _ in range(max(1, count)):
        if combo:
            keys = [k.strip() for k in key.replace("+", " ").split()]
            backend.hotkey(*keys, input_mode=input_mode)
        elif modifier:
            backend.hotkey(_MODIFIER_ALIASES[key.lower().strip()], input_mode=input_mode)
        else:
            backend.press_key(key=key, input_mode=input_mode)
    return {"method": "hotkey" if (combo or modifier) else "key",
            "combo": key if combo else None}


def paste_text(backend, text: str) -> bool:
    """Insert ``text`` via clipboard paste (Ctrl+V), preserving the clipboard.

    Returns True if the paste was **delivered** (clipboard set + Ctrl+V sent) —
    which is NOT the same as landed: CEF/Chromium controls silently drop a
    synthetic Ctrl+V. Always pair this with verification before trusting it; it
    is the last rung of :func:`smart_type_text`, reached only after a keystroke
    attempt is *proven* to have failed.
    """
    try:
        saved = backend.clipboard_get()
    except Exception:
        saved = None
    delivered = False
    try:
        backend.clipboard_set(text)
        backend.hotkey("ctrl", "v")
        time.sleep(0.06)  # let the target consume the clipboard before restoring
        delivered = True
    except Exception:
        delivered = False
    if saved is not None:
        try:
            backend.clipboard_set(saved)
        except Exception:
            pass
    return delivered


def smart_type_text(
    backend,
    text: str,
    *,
    wpm: int = 120,
    input_mode: str = "normal",
    verify: bool = True,
    app: Optional[str] = None,
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
    ref: Optional[str] = None,
) -> dict:
    """Reliably insert ``text`` into the focused control — shared by CLI + MCP.

    Reliability ladder (each rung exact; fall through only if it cannot apply):

    1. **writable ValuePattern** — instant, IME-immune, self-verifying (the
       backend reads the value back). Used when the focused control exposes it.
    2. **keystroke, profile="human"** — the reliable default. Unicode SendInput
       bypasses CJK/TSF IMEs, and the human profile honours ``wpm`` so no
       characters drop. This is what works on CEF/Chromium controls that expose
       no ValuePattern (e.g. DingTalk's message box).
    3. **clipboard paste** — ONLY when verification proves the keystrokes were
       swallowed (an IME or other interceptor ate them). Paste never pre-empts
       keystroke: a synthetic Ctrl+V is silently dropped by CEF, so pasting
       first would hide the failure instead of surfacing it.

    Args:
        backend: Platform backend instance.
        text: Text to insert.
        wpm: Words per minute for the keystroke rung.
        input_mode: "normal" or "hardware" (Phys32 scan codes). ValuePattern and
            paste only apply to "normal"; "hardware" always uses scan codes.
        verify: Capture before-state and verify the result (enables the paste
            fallback). Off skips both reads for speed.
        app/window_title/hwnd/ref: Target hints for verification lookups.

    Returns:
        ``{"method": "value_pattern"|"keystroke"|"clipboard_paste",
           "verified": True|False|None}``.
    """
    # Rung 1: ValuePattern — self-verifying, so a True here is trustworthy.
    if input_mode == "normal":
        try:
            if backend.set_focused_element_value(text, append=True):
                return {"method": "value_pattern", "verified": True}
        except Exception as exc:
            logger.debug("smart_type: ValuePattern rung not applicable: %s", exc)

    # Capture before-state so a swallowed keystroke can be positively detected.
    before: dict = {}
    do_verify = verify and input_mode == "normal"
    if do_verify:
        try:
            from naturo.verify import capture_before_state
            before = capture_before_state(
                backend, action="type", ref=ref, app=app,
                window_title=window_title, hwnd=hwnd,
            ) or {}
        except Exception as exc:
            logger.debug("smart_type: before-state capture failed: %s", exc)

    # Rung 2: keystroke — the reliable default.
    backend.type_text(text=text, wpm=wpm, input_mode=input_mode, profile="human")
    method = "keystroke"
    verified: Optional[bool] = None

    if do_verify:
        try:
            from naturo.verify import verify_type
            result = verify_type(
                backend, text=text, ref=ref, app=app,
                window_title=window_title, hwnd=hwnd,
                before_value=before.get("value"),
                before_ui_texts=before.get("ui_texts"),
            )
            verified = result.verified
            # Rung 3: paste ONLY when keystroke is proven to have failed.
            if verified is False and paste_text(backend, text):
                method = "clipboard_paste"
                recheck = verify_type(
                    backend, text=text, ref=ref, app=app,
                    window_title=window_title, hwnd=hwnd,
                    before_value=before.get("value"),
                    before_ui_texts=before.get("ui_texts"),
                    paste_mode=True,
                )
                verified = recheck.verified
        except Exception as exc:
            logger.debug("smart_type: verification failed: %s", exc)

    return {"method": method, "verified": verified}
