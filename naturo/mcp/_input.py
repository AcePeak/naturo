"""MCP tools for mouse and keyboard input."""
from __future__ import annotations

import logging
import re
from typing import Optional

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
        return {"success": True, "method": method}

    @server.tool()
    @_safe_tool
    def type_text(
        text: str,
        wpm: int = 120,
        input_mode: str = "normal",
        method: str = "auto",
    ) -> dict:
        """Type text using keyboard input.

        Types the given text character by character, simulating human typing.

        Args:
            text: Text to type.
            wpm: Words per minute (typing speed).
            input_mode: Input method — "normal" (default) or "hardware" (Phys32 scan codes, bypasses anti-cheat).
            method: Interaction method override — "auto" (default), "cdp", "uia", "msaa", "ia2", "jab", "vision".

        Returns:
            Dict with success flag.
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
        # (#1219) Prefer IME-immune entry: keystroke injection (SendInput) is
        # intercepted by CJK/TSF IMEs and can corrupt text ("naturo" ->
        # "nature"). When the focused control exposes a writable ValuePattern,
        # set its value directly through UIA — bypassing the keyboard and the
        # IME. Fall back to keystrokes when there is no such control, or when
        # the caller explicitly asked for keystroke-level "hardware" scan codes.
        used_value_pattern = False
        if input_mode == "normal":
            used_value_pattern = bool(backend.set_focused_element_value(text, append=True))
        if not used_value_pattern:
            backend.type_text(text=text, wpm=wpm, input_mode=input_mode)
        return {"success": True, "method": "value_pattern" if used_value_pattern else "keystroke"}

    @server.tool()
    @_safe_tool
    def press_key(key: str, count: int = 1, input_mode: str = "normal", method: str = "auto") -> dict:
        """Press a key or key combination.

        For single keys pass the key name (e.g. "enter", "tab").
        For combos use '+' notation (e.g. "ctrl+c", "alt+f4").

        Args:
            key: Key name or combo string (e.g. "enter", "ctrl+c", "alt+f4").
            count: Number of times to press.
            input_mode: Input method — "normal" (default) or "hardware" (Phys32 scan codes).
            method: Interaction method override — "auto" (default), "cdp", "uia", "msaa", "ia2", "jab", "vision".

        Returns:
            Dict with success flag.
        """
        if count < 1:
            return {"success": False, "error": {"code": "INVALID_INPUT", "message": f"count must be >= 1, got {count}"}}
        backend = _get_backend()
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
