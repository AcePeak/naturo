"""Mouse interaction: click, scroll, drag, and cursor movement."""

from __future__ import annotations

from typing import Optional

from naturo.backends.windows._core import heal_core_on_failure
from naturo.backends.windows._strategies import get_input_strategy


class MouseMixin:
    """Mouse interaction: click, scroll, drag, and cursor movement."""

    @heal_core_on_failure(retry=False)
    def click(self, x: Optional[int] = None, y: Optional[int] = None,
              element_id: Optional[str] = None, button: str = "left",
              double: bool = False, input_mode: str = "normal",
              hwnd: Optional[int] = None) -> None:
        """Click at coordinates or on a UI element.

        If an element_id is provided, finds the element first and clicks its
        center. If x/y coordinates are provided, moves to them first.
        At least one of x/y or element_id must be given.

        Args:
            x: Target X coordinate. Required if element_id not given.
            y: Target Y coordinate. Required if element_id not given.
            element_id: Automation element ID to find and click.
            button: Mouse button — "left", "right", or "middle".
            double: True for double-click.
            input_mode: Ignored for now (Phase 3 will add hardware/hook modes).
            hwnd: Target window handle for element search.  When provided,
                searches within this window instead of the foreground
                window (#525).

        Raises:
            ValueError: If neither coordinates nor element_id is provided.
            ElementNotFoundError: When element_id is given but not found.
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()
        strategy = get_input_strategy(core, input_mode)

        BUTTON_MAP = {"left": 0, "right": 1, "middle": 2}
        btn = BUTTON_MAP.get(button.lower(), 0)

        if element_id is not None:
            # Find element and click its center
            el = self.find_element(selector=element_id, hwnd=hwnd)
            if el is None:
                from naturo.errors import ElementNotFoundError
                raise ElementNotFoundError(element_id)
            cx = el.x + el.width // 2
            cy = el.y + el.height // 2
            strategy.click(cx, cy, btn, double)
        elif x is not None and y is not None:
            strategy.click(x, y, btn, double)
        else:
            raise ValueError("click: provide either (x, y) or element_id")

    def scroll(self, direction: str = "down", amount: int = 3,
               x: Optional[int] = None, y: Optional[int] = None,
               smooth: bool = False) -> None:
        """Scroll the mouse wheel.

        Args:
            direction: "up", "down", "left", or "right".
            amount: Number of wheel notches (each = 120 delta units).
            x: Move mouse to this X before scrolling. None = current position.
            y: Move mouse to this Y before scrolling. None = current position.
            smooth: Ignored (Phase 3 will add smooth scroll support).

        Raises:
            NaturoCoreError: On system error.
        """
        core = self._ensure_core()
        strategy = get_input_strategy(core)

        if x is not None and y is not None:
            core.mouse_move(x, y)

        WHEEL_DELTA = 120
        horizontal = direction in ("left", "right")
        # Up/right = positive, Down/left = negative
        sign = 1 if direction in ("up", "right") else -1
        delta = sign * amount * WHEEL_DELTA

        strategy.scroll(delta, horizontal)

    def drag(self, from_x: int = 0, from_y: int = 0, to_x: int = 0, to_y: int = 0,
             duration_ms: int = 500, steps: int = 10,
             trajectory: str = "linear", jitter: float = 0.0,
             overshoot: float = 0.0, release_delay_ms: int = 0) -> None:
        """Drag from one point to another.

        Moves mouse to (from_x, from_y), holds left button, follows a
        trajectory to (to_x, to_y), then releases the button.

        Args:
            from_x: Source X coordinate.
            from_y: Source Y coordinate.
            to_x: Destination X coordinate.
            to_y: Destination Y coordinate.
            duration_ms: Total drag duration in milliseconds.
            steps: Number of intermediate move steps.
            trajectory: Motion mode — ``"linear"`` (default), ``"bezier"``,
                or ``"instant"``.
            jitter: Max random perpendicular offset per step (pixels).
            overshoot: Pixels to overshoot past target then correct back.
            release_delay_ms: Pause in ms before releasing the button.

        Raises:
            NaturoCoreError: On system error.
        """
        import time
        from naturo.backends.windows._trajectory import generate_trajectory

        core = self._ensure_core()

        points = generate_trajectory(
            from_x, from_y, to_x, to_y,
            mode=trajectory, duration_ms=duration_ms, steps=steps,
            jitter=jitter, overshoot=overshoot,
        )

        core.mouse_move(from_x, from_y)
        time.sleep(0.05)  # Brief settle before pressing
        core.mouse_down(0)  # Press and hold left button

        try:
            for pt in points:
                core.mouse_move(pt.x, pt.y)
                if pt.delay_s > 0:
                    time.sleep(pt.delay_s)
            if release_delay_ms > 0:
                time.sleep(release_delay_ms / 1000.0)
        finally:
            core.mouse_up(0)  # Always release, even on error

    def move_mouse(self, x: int = 0, y: int = 0, *,
                   trajectory: str = "instant",
                   duration_ms: int = 500, steps: int | None = None,
                   jitter: float = 0.0, overshoot: float = 0.0) -> None:
        """Move the mouse cursor to absolute screen coordinates.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            trajectory: Motion mode — ``"instant"`` (default, teleport),
                ``"linear"``, or ``"bezier"`` (human-like).
            duration_ms: Total movement time in milliseconds (non-instant modes).
            steps: Number of intermediate points (auto-calculated if omitted).
            jitter: Max random perpendicular offset per step (pixels).
            overshoot: Pixels to overshoot past target then correct back.

        Raises:
            NaturoCoreError: On system error.
        """
        import time
        from naturo.backends.windows._trajectory import generate_trajectory

        core = self._ensure_core()

        if trajectory == "instant":
            core.mouse_move(x, y)
            return

        # Get current cursor position as trajectory start
        try:
            import ctypes
            from ctypes import wintypes
            point = wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(point))  # type: ignore[union-attr]
            start_x, start_y = point.x, point.y
        except Exception:
            # Non-Windows or error: just teleport
            core.mouse_move(x, y)
            return

        points = generate_trajectory(
            start_x, start_y, x, y,
            mode=trajectory, duration_ms=duration_ms, steps=steps,
            jitter=jitter, overshoot=overshoot,
        )

        for pt in points:
            core.mouse_move(pt.x, pt.y)
            if pt.delay_s > 0:
                time.sleep(pt.delay_s)
