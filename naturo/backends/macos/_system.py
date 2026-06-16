"""System interaction — clipboard access and dialog handling."""
from __future__ import annotations

from typing import Optional

from naturo.backends.macos._peekaboo import PeekabooError


class SystemMixin:
    """Clipboard and dialog interaction via Peekaboo."""

    # === Clipboard ===

    def clipboard_get(self) -> str:
        """Get clipboard text content.

        Returns:
            Current clipboard text.
        """
        data = self._run(["clipboard", "-a", "get"])
        return data.get("data", {}).get("text", data.get("text", ""))

    def clipboard_set(self, text: str = "") -> None:
        """Set clipboard text content.

        Args:
            text: Text to copy to clipboard.
        """
        self._run(["clipboard", "-a", "set", "--text", text])

    def clipboard_clear(self) -> None:
        """Clear the clipboard contents."""
        self._run(["clipboard", "-a", "clear"])

    # === Dialog ===

    def detect_dialogs(
        self,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> list:
        """Detect active dialog windows.

        Args:
            app: Filter by owner application name.
            hwnd: Filter by specific dialog window handle.

        Returns:
            List of dialog info dicts.
        """
        args = ["dialog", "detect"]
        if app:
            args += ["--app", app]
        try:
            data = self._run(args, timeout=10)
            return data.get("data", {}).get("dialogs", data.get("dialogs", []))
        except PeekabooError:
            return []

    def dialog_click_button(
        self,
        button: str,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Click a button in a dialog.

        Args:
            button: Button text to click (e.g., "OK", "Cancel").
            app: Owner application name.
            hwnd: Specific dialog window handle.

        Returns:
            Dict with result info.
        """
        if button.lower() in ("ok", "yes", "accept"):
            args = ["dialog", "accept"]
        elif button.lower() in ("cancel", "no", "dismiss"):
            args = ["dialog", "dismiss"]
        else:
            args = ["dialog", "click-button", button]

        if app:
            args += ["--app", app]
        data = self._run(args)
        return data.get("data", data)

    def dialog_set_input(
        self,
        text: str,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> dict:
        """Type text into a dialog input field.

        Args:
            text: Text to enter.
            app: Owner application name.
            hwnd: Specific dialog window handle.

        Returns:
            Dict with result info.
        """
        args = ["dialog", "type", text]
        if app:
            args += ["--app", app]
        data = self._run(args)
        return data.get("data", data)
