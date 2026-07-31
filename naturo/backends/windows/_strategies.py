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


class PostMessageStrategy(InputStrategy):
    """Window-message input via ``PostMessage`` (no OS input stack).

    Delivers mouse/keyboard input by posting ``WM_*`` messages directly to
    the target window, instead of injecting into the session-wide input
    stream with ``SendInput``.  This is the only mechanism that works in a
    **headless/disconnected session** (an RDP session with no attached,
    rendering client, or a ``tscon``-redirected console) where synthetic
    input is silently dropped: there ``SendInput``/``SetCursorPos`` succeed
    but move nothing and actuate nothing.

    Because the messages are posted to a specific ``HWND`` rather than the
    shared input queue, this bypasses that dead input stack — and, when the
    driving process is **elevated**, it also bypasses UIPI, so it can drive
    higher-integrity windows (e.g. security suites).  It works for classic
    Win32 controls and for single-HWND custom/self-drawn toolkits such as Qt
    (whose window proc dispatches the posted message to the widget at the
    given client coordinates), where UIA/MSAA expose nothing.

    Trade-offs vs. ``SendInput``: no real cursor movement (some apps that
    read the global cursor rather than the message's ``lParam`` may not
    react), and keystrokes go to the foreground window's focus.  Locate
    targets by element geometry / vision, then post by client coordinate.
    """

    #: Per-button (down, up, dblclk, wParam-when-pressed) message quads.
    _BTN = {
        0: (0x0201, 0x0202, 0x0203, 0x0001),  # left:   DOWN/UP/DBLCLK, MK_LBUTTON
        1: (0x0204, 0x0205, 0x0206, 0x0002),  # right:  DOWN/UP/DBLCLK, MK_RBUTTON
        2: (0x0207, 0x0208, 0x0209, 0x0010),  # middle: DOWN/UP/DBLCLK, MK_MBUTTON
    }
    _WM_MOUSEMOVE = 0x0200
    _WM_MOUSEWHEEL = 0x020A
    _WM_CHAR = 0x0102
    _WM_KEYDOWN = 0x0100
    _WM_KEYUP = 0x0101

    def __init__(self, core: NaturoCore) -> None:
        self._core = core  # kept for interface symmetry; not used for delivery

    @staticmethod
    def _u32():
        import ctypes
        return ctypes.windll.user32  # type: ignore[union-attr]

    def _target_at(self, x: int, y: int):
        """Return (hwnd, clientX, clientY) for screen point (x, y)."""
        import ctypes
        from ctypes import wintypes
        u = self._u32()
        pt = wintypes.POINT(x, y)
        hwnd = u.WindowFromPoint(pt)
        if not hwnd:
            return None, x, y
        cpt = wintypes.POINT(x, y)
        u.ScreenToClient(hwnd, ctypes.byref(cpt))
        return hwnd, cpt.x, cpt.y

    @staticmethod
    def _lparam(x: int, y: int) -> int:
        return ((y & 0xFFFF) << 16) | (x & 0xFFFF)

    def _foreground(self):
        return self._u32().GetForegroundWindow()

    def click(self, x: int, y: int, button: int = 0,
              double: bool = False) -> None:
        import time
        u = self._u32()
        hwnd, cx, cy = self._target_at(x, y)
        if not hwnd:
            raise RuntimeError(f"PostMessage click: no window at ({x}, {y})")
        down, up, dbl, mk = self._BTN.get(button, self._BTN[0])
        lp = self._lparam(cx, cy)
        u.PostMessageW(hwnd, self._WM_MOUSEMOVE, 0, lp)
        time.sleep(0.02)
        u.PostMessageW(hwnd, down, mk, lp)
        time.sleep(0.02)
        u.PostMessageW(hwnd, up, 0, lp)
        if double:
            time.sleep(0.02)
            u.PostMessageW(hwnd, dbl, mk, lp)
            time.sleep(0.02)
            u.PostMessageW(hwnd, up, 0, lp)

    def type_text(self, text: str, delay_ms: int = 5) -> None:
        import time
        u = self._u32()
        hwnd = self._foreground()
        if not hwnd:
            raise RuntimeError("PostMessage type_text: no foreground window")
        for ch in text:
            u.PostMessageW(hwnd, self._WM_CHAR, ord(ch), 1)
            if delay_ms:
                time.sleep(delay_ms / 1000.0)

    def press_key(self, key: str) -> None:
        import time
        u = self._u32()
        hwnd = self._foreground()
        if not hwnd:
            raise RuntimeError("PostMessage press_key: no foreground window")
        vk = _VK_MAP.get(key.lower())
        if vk is None:
            if len(key) == 1:
                vk = ord(key.upper())
            else:
                raise ValueError(f"PostMessage press_key: unknown key {key!r}")
        u.PostMessageW(hwnd, self._WM_KEYDOWN, vk, 1)
        time.sleep(0.02)
        u.PostMessageW(hwnd, self._WM_KEYUP, vk, 1)

    def hotkey(self, *keys: str) -> None:
        # WM_KEYDOWN/UP cannot faithfully model held modifiers via PostMessage
        # (no shared keyboard state); fall back to SendInput for combos.
        SendInputStrategy(self._core).hotkey(*keys)

    def scroll(self, delta: int, horizontal: bool = False) -> None:
        import ctypes
        from ctypes import wintypes
        u = self._u32()
        pt = wintypes.POINT()
        u.GetCursorPos(ctypes.byref(pt))
        hwnd, _, _ = self._target_at(pt.x, pt.y)
        if not hwnd:
            hwnd = self._foreground()
        wm = 0x020E if horizontal else self._WM_MOUSEWHEEL  # WM_MOUSEHWHEEL
        wparam = (delta & 0xFFFF) << 16
        u.PostMessageW(hwnd, wm, wparam, self._lparam(pt.x, pt.y))


#: Common key-name -> virtual-key code for PostMessage keyboard events.
_VK_MAP = {
    "enter": 0x0D, "return": 0x0D, "tab": 0x09, "esc": 0x1B, "escape": 0x1B,
    "space": 0x20, "backspace": 0x08, "delete": 0x2E, "del": 0x2E,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74, "f6": 0x75,
    "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B,
}


#: Process-cached result of the input-stack liveness probe (None = not probed).
_INPUT_STACK_ALIVE: bool | None = None


def _input_stack_alive() -> bool:
    """Return whether synthetic mouse input actually moves the cursor.

    In a **headless/disconnected session** (an RDP session whose client is
    detached or not rendering, or a ``tscon``-redirected console with no
    input device) ``SetCursorPos``/``SendInput`` succeed but the cursor does
    not move and nothing is actuated — so the default ``SendInput`` path
    silently no-ops.  This probes the ground truth by nudging the cursor a
    few pixels and reading it back, restoring the original position.

    The result is cached for the process (the session's input state is
    stable across a normal run; short-lived CLI invocations re-probe on each
    launch).  On any error, or off-Windows, it assumes the stack is alive so
    behaviour never regresses from the historical ``SendInput`` default.
    """
    global _INPUT_STACK_ALIVE
    if _INPUT_STACK_ALIVE is not None:
        return _INPUT_STACK_ALIVE
    _INPUT_STACK_ALIVE = _probe_cursor_movement()
    if not _INPUT_STACK_ALIVE:
        logger.info(
            "input-stack probe: synthetic cursor movement has no effect "
            "(headless/disconnected session) -> defaulting to PostMessage input"
        )
    return _INPUT_STACK_ALIVE


def _probe_cursor_movement() -> bool:
    """Nudge the cursor and check it moved; restore it. True = input works."""
    try:
        import ctypes
        from ctypes import wintypes

        u = ctypes.windll.user32  # type: ignore[union-attr]
        orig = wintypes.POINT()
        if not u.GetCursorPos(ctypes.byref(orig)):
            return True  # cannot read cursor -> don't regress
        cur = wintypes.POINT()
        for dx, dy in ((5, 5), (-5, -5)):
            u.SetCursorPos(orig.x + dx, orig.y + dy)
            u.GetCursorPos(ctypes.byref(cur))
            if cur.x != orig.x or cur.y != orig.y:
                u.SetCursorPos(orig.x, orig.y)  # restore
                return True
        u.SetCursorPos(orig.x, orig.y)  # restore
        return False
    except Exception:
        return True  # off-Windows or probe failure -> assume alive


def get_input_strategy(
    core: NaturoCore,
    input_mode: str = "normal",
) -> InputStrategy:
    """Select the appropriate input strategy.

    Args:
        core: Loaded ``NaturoCore`` instance.
        input_mode: One of

            * ``"normal"`` / ``"auto"`` (default) — prefer ``SendInput``, but
              **transparently fall back to PostMessage** when a one-time probe
              finds the session's input stack is dead (headless/disconnected).
              Callers get headless support with no extra flags.
            * ``"hardware"`` — Phys32 scan-code driver (keyboard).
            * ``"postmessage"`` — always ``PostMessage`` window-message
              delivery (works headless; needs elevation for higher-integrity
              windows).

    Returns:
        An ``InputStrategy`` implementation.

    Raises:
        ValueError: If ``input_mode`` is not recognized.
    """
    if input_mode == "hardware":
        return Phys32Strategy(core)
    if input_mode == "postmessage":
        return PostMessageStrategy(core)
    if input_mode in ("normal", "auto"):
        if _input_stack_alive():
            return SendInputStrategy(core)
        return PostMessageStrategy(core)
    raise ValueError(
        f"Unknown input_mode {input_mode!r}. "
        f"Supported modes: 'normal'/'auto', 'hardware', 'postmessage'."
    )
