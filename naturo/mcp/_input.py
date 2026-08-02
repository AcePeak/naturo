"""MCP tools for mouse and keyboard input."""
from __future__ import annotations

import logging
import re
from typing import Optional

from naturo.mcp._resolve import require_hwnd

logger = logging.getLogger(__name__)

_EN_REF_RE = re.compile(r"e\d+")


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
    ) -> dict:
        """Click at coordinates or on a UI element.

        Provide either (x, y) coordinates or an element_id from see_ui_tree/find_element.

        Args:
            x: X coordinate.
            y: Y coordinate.
            element_id: Element ID to click (eN ref from see_ui_tree, or selector from find_element).
            button: Mouse button — "left", "right", or "middle".
            double: Double-click if True.
            input_mode: Input method — "normal" (default) or "hardware" (Phys32, bypasses anti-cheat).
            method: Interaction method override — "auto" (default), "cdp", "uia", "msaa", "ia2", "jab", "vision". Bypasses auto-detection when set explicitly.

        Returns:
            Dict with success flag.
        """
        # (#682) Resolve eN refs from see_ui_tree snapshots to coordinates.
        if element_id and _EN_REF_RE.fullmatch(element_id):
            from naturo.snapshot import get_snapshot_manager
            mgr = get_snapshot_manager()
            resolved = mgr.resolve_ref(element_id)
            if resolved:
                logger.debug("Resolved MCP ref %s → (%d, %d)", element_id, resolved[0], resolved[1])
                x, y = resolved[0], resolved[1]
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
        backend.click(x=x, y=y, element_id=element_id, button=button, double=double,
                      input_mode=input_mode)
        result: dict = {"success": True, "method": method}
        # (#1207) Report which top-level window the click actually landed on, so
        # the MCP click — like the CLI click — never blindly claims success on an
        # overlapping window or after a failed foreground switch.
        if x is not None and y is not None:
            from naturo.window import window_root_at_point
            hit = window_root_at_point(x, y)
            if hit:
                result["hit_window"] = {"hwnd": hit[0], "title": hit[1], "pid": hit[2]}
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
        # Delegate to the shared reliability ladder in naturo/actions.py so this
        # MCP tool and the CLI `type` command cannot drift apart. The ladder is:
        #   1. writable ValuePattern (instant, IME-immune, self-verifying);
        #   2. keystroke, profile="human" (Unicode bypasses CJK/TSF IMEs, no drop);
        #   3. clipboard paste — LAST, and only on a *proven* keystroke failure.
        # The old MCP order pasted before keystroke and never verified it, so it
        # silently "succeeded" on CEF controls (DingTalk) that drop synthetic Ctrl+V.
        from naturo.actions import smart_type_text
        outcome = smart_type_text(
            backend, text, wpm=wpm, input_mode=input_mode,
            hwnd=hwnd, window_title=window_title,
        )
        return {"success": True, **outcome}

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
        # Shared press logic (naturo/actions.py): a '+'-combo OR a lone modifier
        # (alt/ctrl/shift/win) routes through hotkey — the bridge can't hold a
        # bare modifier — so `press_key("alt")` no longer silently no-ops here as
        # it did before, matching the CLI `press` command.
        from naturo.actions import smart_press_key
        outcome = smart_press_key(backend, key, count=count, input_mode=input_mode)
        result: dict = {"success": True}
        if outcome["method"] == "hotkey":
            result["action"] = "hotkey"
            if outcome["combo"]:
                result["combo"] = outcome["combo"]
        return result

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
