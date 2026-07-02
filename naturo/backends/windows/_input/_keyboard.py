"""Keyboard interaction: text typing, key presses, and hotkey combinations."""

from __future__ import annotations

from naturo.backends.windows._core import heal_core_on_failure
from naturo.backends.windows._strategies import get_input_strategy


class KeyboardMixin:
    """Keyboard interaction: text typing, key presses, and hotkey combinations."""

    @heal_core_on_failure(retry=False)
    def type_text(self, text: str = "", delay_ms: int = 5, profile: str = "linear",
                  wpm: int = 120, input_mode: str = "normal") -> None:
        """Type text using SendInput.

        Args:
            text: UTF-8 string to type.
            delay_ms: Delay between keystrokes (milliseconds). Default: 5.
                For "human" profile, this is the base delay.
            profile: "linear" for constant delay, "human" for variable speed.
                     Human profile uses wpm to calculate delay.
            wpm: Words per minute (used only when profile="human").
            input_mode: Input method — "normal" (virtual key / Unicode) or
                "hardware" (scan code / Phys32, bypasses game anti-cheat).

        Raises:
            NaturoCoreError: On system error.
        """
        import re

        core = self._ensure_core()
        strategy = get_input_strategy(core, input_mode)

        actual_delay = delay_ms
        if profile == "human" and wpm > 0:
            # Average word = 5 chars, convert wpm to ms per char
            ms_per_char = int(60_000 / (wpm * 5))
            actual_delay = max(1, ms_per_char)

        # (#840) SendInput's UNICODE path silently drops \n and \r
        # control characters.  Split on line breaks and press Enter
        # between segments so multiline text is typed correctly.
        segments = re.split(r"\r\n|\r|\n", text)
        for i, segment in enumerate(segments):
            if segment:
                strategy.type_text(segment, actual_delay)
            if i < len(segments) - 1:
                strategy.press_key("enter")

    def press_key(self, key: str = "", input_mode: str = "normal") -> None:
        """Press and release a named key.

        Args:
            key: Key name (enter, tab, escape, f1-f12, a-z, 0-9, etc.).
            input_mode: Input method — "normal" (virtual key) or
                "hardware" (scan code / Phys32).

        Raises:
            NaturoCoreError: If key name is unrecognized or on system error.
        """
        core = self._ensure_core()
        strategy = get_input_strategy(core, input_mode)
        strategy.press_key(key)

    def hotkey(self, *keys: str, hold_duration_ms: int = 50,
              input_mode: str = "normal") -> None:
        """Press a hotkey combination.

        Args:
            *keys: Key names. Modifiers (ctrl, alt, shift, win) are recognized
                   automatically. One non-modifier key is the base key.
            hold_duration_ms: Not yet used.
            input_mode: Input method — "normal" (virtual key) or
                "hardware" (scan code / Phys32).

        Example:
            backend.hotkey("ctrl", "c")   # Copy
            backend.hotkey("ctrl", "z")   # Undo

        Raises:
            NaturoCoreError: On invalid argument or system error.
        """
        core = self._ensure_core()
        strategy = get_input_strategy(core, input_mode)
        strategy.hotkey(*keys)
