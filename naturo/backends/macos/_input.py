"""Input simulation — click, type, key press, scroll, drag, mouse move."""
from __future__ import annotations

from naturo.errors import NaturoError


class InputMixin:
    """Keyboard and mouse input simulation via Peekaboo."""

    def click(
        self,
        x: int = None,
        y: int = None,
        element_id: str = None,
        button: str = "left",
        double: bool = False,
        input_mode: str = "normal",
    ) -> None:
        """Click at coordinates or on an element.

        Args:
            x: X coordinate for click.
            y: Y coordinate for click.
            element_id: Peekaboo element ID to click.
            button: Mouse button ('left', 'right', 'middle').
            double: Whether to double-click.
            input_mode: Input mode (only 'normal' on macOS).

        Raises:
            NaturoError: If neither coordinates nor element_id is provided.
        """
        args = ["click"]
        if element_id:
            args += [element_id]
        elif x is not None and y is not None:
            args += ["--x", str(x), "--y", str(y)]
        else:
            raise NaturoError("Either coordinates (x, y) or element_id must be specified")

        if button == "right":
            args.append("--right")
        if double:
            args.append("--double")

        self._run(args)

    def type_text(
        self,
        text: str = "",
        delay_ms: int = 5,
        profile: str = "human",
        wpm: int = 120,
        input_mode: str = "normal",
    ) -> None:
        """Type text using keyboard simulation.

        Args:
            text: Text to type.
            delay_ms: Delay between keystrokes in milliseconds.
            profile: Typing profile (ignored on macOS).
            wpm: Words per minute (ignored on macOS).
            input_mode: Input mode (only 'normal' on macOS).
        """
        if not text:
            return
        args = ["type", text]
        if delay_ms > 0:
            # Peekaboo uses --delay in seconds
            args += ["--delay", str(delay_ms / 1000.0)]
        self._run(args)

    def press_key(self, key: str = "", input_mode: str = "normal") -> None:
        """Press a single key or key combination.

        Args:
            key: Key name (e.g., 'enter', 'tab', 'escape').
            input_mode: Input mode (only 'normal' on macOS).
        """
        if not key:
            return
        self._run(["press", key])

    def hotkey(self, *keys: str, hold_duration_ms: int = 50) -> None:
        """Press a keyboard shortcut.

        Args:
            *keys: Key names to press simultaneously (e.g., 'cmd', 's').
            hold_duration_ms: Duration to hold keys in milliseconds.
        """
        if not keys:
            return
        # Peekaboo hotkey expects keys joined with +
        combo = "+".join(keys)
        self._run(["hotkey", combo])

    def scroll(
        self,
        direction: str = "down",
        amount: int = 3,
        x: int = None,
        y: int = None,
        smooth: bool = False,
    ) -> None:
        """Scroll the mouse wheel.

        Args:
            direction: Scroll direction ('up', 'down', 'left', 'right').
            amount: Number of scroll steps.
            x: X coordinate for scroll location.
            y: Y coordinate for scroll location.
            smooth: Whether to use smooth scrolling.
        """
        args = ["scroll", "--direction", direction, "--amount", str(amount)]
        if x is not None and y is not None:
            args += ["--x", str(x), "--y", str(y)]
        self._run(args)

    def drag(
        self,
        from_x: int = 0,
        from_y: int = 0,
        to_x: int = 0,
        to_y: int = 0,
        duration_ms: int = 500,
        steps: int = 10,
        trajectory: str = "linear",
        jitter: float = 0.0,
        overshoot: float = 0.0,
        release_delay_ms: int = 0,
    ) -> None:
        """Drag from one point to another.

        Args:
            from_x: Starting X coordinate.
            from_y: Starting Y coordinate.
            to_x: Ending X coordinate.
            to_y: Ending Y coordinate.
            duration_ms: Drag duration in milliseconds.
            steps: Number of intermediate steps.
            trajectory: Motion mode (ignored on macOS — uses Peekaboo drag).
            jitter: Perpendicular jitter pixels (ignored on macOS).
            overshoot: Overshoot pixels (ignored on macOS).
            release_delay_ms: Pause before release (ignored on macOS).
        """
        args = [
            "drag",
            "--from-x", str(from_x), "--from-y", str(from_y),
            "--to-x", str(to_x), "--to-y", str(to_y),
        ]
        if duration_ms > 0:
            args += ["--duration", str(duration_ms / 1000.0)]
        self._run(args)

    def move_mouse(self, x: int = 0, y: int = 0, *,
                   trajectory: str = "instant",
                   duration_ms: int = 500, steps: int | None = None,
                   jitter: float = 0.0, overshoot: float = 0.0) -> None:
        """Move the mouse cursor to coordinates.

        Args:
            x: Target X coordinate.
            y: Target Y coordinate.
            trajectory: Motion mode (ignored on macOS — always teleports).
            duration_ms: Movement duration (ignored on macOS).
            steps: Interpolation steps (ignored on macOS).
            jitter: Perpendicular jitter (ignored on macOS).
            overshoot: Overshoot pixels (ignored on macOS).
        """
        self._run(["move", "--x", str(x), "--y", str(y)])
