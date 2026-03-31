"""Pluggable input strategies for Windows backend.

Each strategy encapsulates a different mechanism for delivering keyboard
and mouse input to the OS.  The ``get_input_strategy`` factory selects
the appropriate strategy based on ``input_mode``.

Adding a new input method (e.g. MinHook injection) requires only:
1. Subclass ``InputStrategy``
2. Add the mode string to ``get_input_strategy``

No changes to ``InputMixin`` or CLI code are needed.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from naturo.bridge._core import NaturoCore

logger = logging.getLogger(__name__)


class InputStrategy(ABC):
    """Abstract base for input delivery mechanisms.

    Every concrete strategy must implement the five primitives that the
    ``InputMixin`` delegates to.  Strategies are stateless with respect
    to the input they deliver -- the ``NaturoCore`` handle is injected
    at construction time.
    """

    @abstractmethod
    def type_text(self, text: str, delay_ms: int = 5) -> None:
        """Type a UTF-8 string.

        Args:
            text: Text to type.
            delay_ms: Delay between keystrokes in milliseconds.
        """

    @abstractmethod
    def press_key(self, key: str) -> None:
        """Press and release a named key.

        Args:
            key: Key name (e.g. ``"enter"``, ``"tab"``, ``"f5"``).
        """

    @abstractmethod
    def hotkey(self, *keys: str) -> None:
        """Press a hotkey combination.

        Args:
            *keys: Key names.  Modifiers (ctrl, alt, shift, win) are
                detected automatically; one non-modifier key is the
                base key.
        """

    @abstractmethod
    def click(self, x: int, y: int, button: int = 0,
              double: bool = False) -> None:
        """Move the cursor and click.

        Args:
            x: Screen X coordinate.
            y: Screen Y coordinate.
            button: 0 = left, 1 = right, 2 = middle.
            double: ``True`` for double-click.
        """

    @abstractmethod
    def scroll(self, delta: int, horizontal: bool = False) -> None:
        """Scroll the mouse wheel.

        Args:
            delta: Scroll amount (positive = up/right, negative = down/left).
            horizontal: ``True`` for horizontal scrolling.
        """


class SendInputStrategy(InputStrategy):
    """Default virtual-key / Unicode input via Win32 ``SendInput``.

    This is the standard strategy for most applications.
    """

    def __init__(self, core: NaturoCore) -> None:
        self._core = core

    def type_text(self, text: str, delay_ms: int = 5) -> None:
        self._core.key_type(text, delay_ms)

    def press_key(self, key: str) -> None:
        self._core.key_press(key)

    def hotkey(self, *keys: str) -> None:
        self._core.key_hotkey(*keys)

    def click(self, x: int, y: int, button: int = 0,
              double: bool = False) -> None:
        self._core.mouse_move(x, y)
        self._core.mouse_click(button, double)

    def scroll(self, delta: int, horizontal: bool = False) -> None:
        self._core.mouse_scroll(delta, horizontal)


class Phys32Strategy(InputStrategy):
    """Hardware scan-code input via the Phys32 driver.

    Uses ``KEYEVENTF_SCANCODE`` to send raw PS/2 scan codes, which are
    harder for games and anti-cheat software to detect as synthetic
    input.  Mouse operations fall through to ``SendInput`` because
    Phys32 only covers the keyboard.
    """

    def __init__(self, core: NaturoCore) -> None:
        self._core = core

    def type_text(self, text: str, delay_ms: int = 5) -> None:
        self._core.phys_key_type(text, delay_ms)

    def press_key(self, key: str) -> None:
        self._core.phys_key_press(key)

    def hotkey(self, *keys: str) -> None:
        self._core.phys_key_hotkey(*keys)

    def click(self, x: int, y: int, button: int = 0,
              double: bool = False) -> None:
        # Phys32 only covers keyboard; mouse is always SendInput.
        self._core.mouse_move(x, y)
        self._core.mouse_click(button, double)

    def scroll(self, delta: int, horizontal: bool = False) -> None:
        self._core.mouse_scroll(delta, horizontal)


def get_input_strategy(
    core: NaturoCore,
    input_mode: str = "normal",
) -> InputStrategy:
    """Select the appropriate input strategy.

    Args:
        core: Loaded ``NaturoCore`` instance.
        input_mode: ``"normal"`` for SendInput, ``"hardware"`` for Phys32.

    Returns:
        An ``InputStrategy`` implementation.

    Raises:
        ValueError: If ``input_mode`` is not recognized.
    """
    if input_mode == "hardware":
        return Phys32Strategy(core)
    if input_mode == "normal":
        return SendInputStrategy(core)
    raise ValueError(
        f"Unknown input_mode {input_mode!r}. "
        f"Supported modes: 'normal', 'hardware'."
    )
