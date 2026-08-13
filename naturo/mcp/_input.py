"""MCP tools for mouse and keyboard input."""
from __future__ import annotations

import logging
import re
from typing import Optional

from naturo.mcp._resolve import require_hwnd
# (#1318) Shared landing-window hit test + cross-PID verdict — the SAME
# implementation the CLI ``naturo click`` uses (naturo.hit_verify), so both
# surfaces return an identical honesty verdict. Bound as module-local names so
# tests can patch them (naturo.mcp._input._window_root_at_point / _window_pid).
from naturo.hit_verify import (
    CLICK_WRONG_WINDOW,
    hit_window_dict as _hit_window_dict,
    is_cross_pid_mismatch as _is_cross_pid_mismatch,
    window_pid as _window_pid,
    window_root_at_point as _window_root_at_point,
    wrong_window_message as _wrong_window_message,
)

logger = logging.getLogger(__name__)

_EN_REF_RE = re.compile(r"e\d+")


def _paste_text(backend, text: str) -> bool:
    """Backward-compatible thin wrapper around :func:`naturo.actions.paste_text`.

    The clipboard-paste helper now lives in ``naturo.actions`` so the CLI and
    MCP share ONE implementation of the type ladder (#1219). This wrapper keeps
    ``naturo.mcp._input._paste_text`` importable for existing callers/tests.
    """
    from naturo.actions import paste_text
    return paste_text(backend, text)


def register_input_tools(server, _get_backend, _safe_tool):
    """Register input action MCP tools."""

    @server.tool()
    @_safe_tool
    def click(
        x: Optional[int] = None,
        y: Optional[int] = None,
        element_id: Optional[str] = None,
        button: str = "left",
        double: bool = False,
        input_mode: str = "normal",
        method: str = "auto",
        hwnd: Optional[int] = None,
        window_title: Optional[str] = None,
    ) -> dict:
        """Click at coordinates or on a UI element.

        Provide either (x, y) coordinates or an element_id from see_ui_tree/find_element.

        Pass ``hwnd`` (from ``launch_app``/``list_windows``) or ``window_title``
        to name the target window: naturo focuses it first so the click lands
        there, and — crucially — after the click it checks the window actually
        under the point. If the click landed on a *different process'* window
        (the target was occluded or never came to the foreground), the tool
        returns ``success:false`` with ``CLICK_WRONG_WINDOW`` instead of a false
        success (#1318, the Never-Lie parity fix that #1207 shipped on the CLI).
        A cached eN ref carries its own source window, so eN clicks are verified
        the same way with no extra argument. For bare (x, y) with no known
        target, the landing window is disclosed in ``hit_window``.

        Args:
            x: X coordinate.
            y: Y coordinate.
            element_id: Element ID to click (eN ref from see_ui_tree, or selector from find_element).
            button: Mouse button — "left", "right", or "middle".
            double: Double-click if True.
            input_mode: Input method — "normal" (default) or "hardware" (Phys32, bypasses anti-cheat).
            method: Interaction method override — "auto" (default), "cdp", "uia", "msaa", "ia2", "jab", "vision". Bypasses auto-detection when set explicitly.
            hwnd: Target window handle — focus + verify the click landed on it.
            window_title: Target window title (partial match) — focus + verify.

        Returns:
            Dict with a success flag. On a coordinate/eN click it also carries
            ``verified`` (True when the click was confirmed to land on the known
            target's process, else null) and, when determinable, ``hit_window``
            (the window actually under the click point). On a cross-process
            landing mismatch it is a ``success:false`` / ``CLICK_WRONG_WINDOW``
            envelope instead.
        """
        # (#1207/#1318) Track the intended target window so the post-click hit
        # test can confirm the click actually reached it. It is known via an
        # explicit hwnd/window_title selector or a cached eN snapshot; it is
        # unknown for a bare (x, y) click (naturo cannot infer intent there).
        target_hwnd: Optional[int] = None

        # (#682) Resolve eN refs from see_ui_tree snapshots to coordinates.
        if element_id and _EN_REF_RE.fullmatch(element_id):
            from naturo.snapshot import get_snapshot_manager
            mgr = get_snapshot_manager()
            resolved = mgr.resolve_ref(element_id)
            if resolved:
                logger.debug("Resolved MCP ref %s → (%d, %d)", element_id, resolved[0], resolved[1])
                x, y = resolved[0], resolved[1]
                # (#1318) The snapshot's source window is the known target for
                # the landing check — mirrors the CLI's cached-HWND path (#448).
                if len(resolved) >= 3:
                    try:
                        snapshot = mgr.get_snapshot(resolved[2])
                        if getattr(snapshot, "window_handle", None):
                            target_hwnd = snapshot.window_handle
                    except Exception as exc:
                        logger.debug("Snapshot HWND retrieval failed: %s", exc)
                element_id = None
            else:
                return {
                    "success": False,
                    "error": {
                        "code": "ELEMENT_NOT_FOUND",
                        "message": f"Element ref '{element_id}' not found. "
                        f"Call see_ui_tree first to capture a snapshot, "
                        f"then use the eN ref from the response.",
                    },
                }

        backend = _get_backend()

        # (#957/#1291) When a window selector is supplied, resolve it loudly —
        # an unresolvable hwnd/window_title raises WindowNotFoundError (mapped to
        # WINDOW_NOT_FOUND) rather than silently clicking the foreground window —
        # then focus it so the click lands there (mirrors the CLI, #608).
        if hwnd is not None or window_title is not None:
            target_hwnd = require_hwnd(backend, window_title=window_title, hwnd=hwnd)
        if target_hwnd:
            try:
                backend.focus_window(hwnd=target_hwnd, title=window_title)
            except Exception as exc:
                logger.debug("Target focus failed (hwnd=%s): %s", target_hwnd, exc)

        backend.click(x=x, y=y, element_id=element_id, button=button, double=double,
                      input_mode=input_mode)

        # (#1318) Landing-window honesty check — the SAME verdict the CLI emits,
        # computed via the shared naturo.hit_verify helpers. When a target was
        # known and the click landed on a different process' window, fail loudly
        # instead of reporting a success that did not happen.
        hit = None
        if x is not None and y is not None:
            hit = _window_root_at_point(x, y)
        verify_target_pid = _window_pid(target_hwnd) if target_hwnd else None
        if hit is not None and _is_cross_pid_mismatch(hit, verify_target_pid):
            return {
                "success": False,
                "error": {
                    "code": CLICK_WRONG_WINDOW,
                    "message": _wrong_window_message(
                        x, y, hit, target_hwnd, verify_target_pid,
                    ),
                },
            }

        result: dict = {"success": True, "method": method}
        # (#1207) Disclose the window actually under a coordinate click, so a
        # caller can see when a bare (x, y) click hit something unexpected.
        if hit:
            result["hit_window"] = _hit_window_dict(hit)
        # (#1318) Mirror the CLI's verified field: a confirmed same-process
        # landing on a *known* target is a positive verification; a bare-coords
        # click (no known intent) or an undeterminable hit stays null.
        result["verified"] = True if (target_hwnd and verify_target_pid and hit) else None
        return result

    @server.tool()
    @_safe_tool
    def type_text(
        text: str,
        wpm: int = 120,
        input_mode: str = "normal",
        method: str = "auto",
        hwnd: Optional[int] = None,
        window_title: Optional[str] = None,
    ) -> dict:
        """Type text into a target window (or the focused window).

        Pass ``hwnd`` (from ``launch_app``/``list_windows``) or ``window_title``
        to type into a specific window: naturo focuses it first so the text
        lands there deterministically — no separate ``focus_window`` call and no
        focus race. Omit both to type into whatever is currently focused.

        Args:
            text: Text to type.
            wpm: Words per minute (applies to the keystroke fallback only).
            input_mode: "normal" (default) or "hardware" (Phys32 scan codes, bypasses anti-cheat).
            method: Interaction method override — "auto" (default), "cdp", "uia", "msaa", "ia2", "jab", "vision".
            hwnd: Target window handle to focus + type into.
            window_title: Target window title (partial match) to focus + type into.

        Returns:
            Dict with success flag and the delivery ``method``.
        """
        if wpm < 1:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"wpm must be >= 1, got {wpm}"}}
        # (#960) Opt-in input-content safety guard. When NATURO_SAFE_INPUT=1 is
        # set (the unattended QA loop), refuse to inject shell-command-like
        # text — a SendInput focus race could otherwise deliver a destructive
        # fragment (e.g. "$(rm -rf /)") to a terminal. Normal users (env unset)
        # are unaffected.
        from naturo.safety import unsafe_input_reason
        unsafe = unsafe_input_reason(text)
        if unsafe:
            return {
                "success": False,
                "error": {
                    "code": "UNSAFE_INPUT_BLOCKED",
                    "message": f"Refusing to inject unsafe content ({unsafe}) because "
                    f"NATURO_SAFE_INPUT=1 is set. Nothing was typed.",
                },
            }
        backend = _get_backend()
        # Optional target: focus the requested window first, in-process and
        # immediately before typing, so the text lands there deterministically —
        # this is one atomic focus+type with no cross-call round-trip for the
        # foreground to drift, the failure mode that made a separate
        # focus_window + type_text land input in the wrong window.
        # (#1291) Resolve the window selector loudly BEFORE focusing. An
        # unresolvable window_title/hwnd raises WindowNotFoundError (mapped to a
        # success:false / WINDOW_NOT_FOUND envelope) instead of silently
        # swallowing the miss and typing into whatever window happens to be
        # focused — the cardinal Never-Lie violation this guards against (#957).
        if hwnd is not None or window_title is not None:
            target_hwnd = require_hwnd(backend, window_title=window_title, hwnd=hwnd)
            backend.focus_window(hwnd=target_hwnd, title=window_title)
        # (#1219) Prefer IME-immune entry: keystroke injection (SendInput) is
        # intercepted by CJK/TSF IMEs and can corrupt text ("naturo" ->
        # "nature"). When the focused control exposes a writable ValuePattern,
        # set its value directly through UIA — bypassing the keyboard and the
        # IME. Fall back to keystrokes when there is no such control, or when
        # the caller explicitly asked for keystroke-level "hardware" scan codes.
        # Reliability ladder (each rung is exact; fall to the next only if it can't apply):
        #   1. writable ValuePattern → set the value directly (instant, IME-immune);
        #   2. clipboard paste → insert atomically (fast, IME-immune, no per-key race) —
        #      this is what heavy controls like Win11 Notepad need, where fast keystroke
        #      SendInput drops chars ("hello from naturo" -> "hello      turo");
        #   3. keystroke at the requested wpm with profile="human" so wpm is honored.
        # The ladder itself lives in naturo.actions.smart_type_text — the SAME
        # helper the CLI ``naturo type`` calls, so the two surfaces can't drift.
        from naturo.actions import smart_type_text
        method = smart_type_text(backend, text, input_mode=input_mode, wpm=wpm)
        return {"success": True, "method": method}

    @server.tool()
    @_safe_tool
    def press_key(key: str, count: int = 1, input_mode: str = "normal", method: str = "auto",
                  hwnd: Optional[int] = None, window_title: Optional[str] = None) -> dict:
        """Press a key or key combination.

        For single keys pass the key name (e.g. "enter", "tab").
        For combos use '+' notation (e.g. "ctrl+c", "alt+f4").

        Args:
            key: Key name or combo string (e.g. "enter", "ctrl+c", "alt+f4").
            count: Number of times to press.
            input_mode: Input method — "normal" (default) or "hardware" (Phys32 scan codes).
            method: Interaction method override — "auto" (default), "cdp", "uia", "msaa", "ia2", "jab", "vision".
            hwnd: Target window handle (from ``launch_app``/``list_windows``) — focuses it
                first so the keys land there, no separate focus_window call and no foreground race.
            window_title: Target window title (partial match) to focus + send to.

        Returns:
            Dict with success flag.
        """
        if count < 1:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"count must be >= 1, got {count}"}}
        backend = _get_backend()
        # (#1291) Loud window resolution — see type_text for rationale (#957).
        if hwnd is not None or window_title is not None:
            target_hwnd = require_hwnd(backend, window_title=window_title, hwnd=hwnd)
            backend.focus_window(hwnd=target_hwnd, title=window_title)
        is_combo = "+" in key
        for _ in range(count):
            if is_combo:
                key_list = [k.strip() for k in key.replace("+", " ").split()]
                backend.hotkey(*key_list, input_mode=input_mode)
            else:
                backend.press_key(key=key, input_mode=input_mode)
        if is_combo:
            return {"success": True, "action": "hotkey", "combo": key}
        return {"success": True}

    @server.tool()
    @_safe_tool
    def hotkey(keys: list[str], input_mode: str = "normal") -> dict:
        """Press a keyboard shortcut (key combination).

        Deprecated: prefer press_key with combo notation (e.g. press_key("ctrl+c")).
        Kept for backward compatibility.

        Args:
            keys: List of keys to press simultaneously (e.g. ["ctrl", "s"] for Ctrl+S).
            input_mode: Input method — "normal" (default) or "hardware" (Phys32 scan codes).

        Returns:
            Dict with success flag.
        """
        if not keys:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": "keys list must not be empty"}}
        backend = _get_backend()
        backend.hotkey(*keys, input_mode=input_mode)
        return {"success": True}

    @server.tool()
    @_safe_tool
    def scroll(
        direction: str = "down",
        amount: int = 3,
        x: Optional[int] = None,
        y: Optional[int] = None,
    ) -> dict:
        """Scroll the mouse wheel.

        Args:
            direction: "up" or "down".
            amount: Number of scroll units.
            x: X coordinate to scroll at (optional).
            y: Y coordinate to scroll at (optional).

        Returns:
            Dict with success flag.
        """
        if amount < 1:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"amount must be >= 1, got {amount}"}}
        backend = _get_backend()
        backend.scroll(direction=direction, amount=amount, x=x, y=y)
        return {"success": True}

    @server.tool()
    @_safe_tool
    def drag(
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        duration_ms: int = 500,
        steps: int = 10,
    ) -> dict:
        """Drag from one point to another.

        Args:
            from_x: Start X coordinate.
            from_y: Start Y coordinate.
            to_x: End X coordinate.
            to_y: End Y coordinate.
            duration_ms: Duration in milliseconds.
            steps: Number of intermediate steps.

        Returns:
            Dict with success flag.
        """
        if steps < 1:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"steps must be >= 1, got {steps}"}}
        if duration_ms < 0:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"duration_ms must be >= 0, got {duration_ms}"}}
        backend = _get_backend()
        backend.drag(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y,
                     duration_ms=duration_ms, steps=steps)
        return {"success": True}

    @server.tool()
    @_safe_tool
    def move_mouse(x: int, y: int) -> dict:
        """Move the mouse cursor to a position.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Dict with success flag.
        """
        backend = _get_backend()
        backend.move_mouse(x=x, y=y)
        return {"success": True}
