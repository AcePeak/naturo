"""macOS backend — wraps the Peekaboo CLI for native macOS automation.

Split into focused submixins for maintainability; the public API is the
single :class:`MacOSBackend` class. ``MacOSBackend`` and ``PeekabooError``
remain importable from ``naturo.backends.macos`` for backward compatibility.
"""
from __future__ import annotations

from naturo.backends.base import Backend
from naturo.backends.macos._app import AppMixin
from naturo.backends.macos._capture import CaptureMixin
from naturo.backends.macos._element import ElementMixin
from naturo.backends.macos._input import InputMixin
from naturo.backends.macos._peekaboo import PeekabooError, _PeekabooRunner
from naturo.backends.macos._system import SystemMixin
from naturo.backends.macos._window import WindowMixin


class MacOSBackend(
    CaptureMixin,
    WindowMixin,
    ElementMixin,
    InputMixin,
    AppMixin,
    SystemMixin,
    _PeekabooRunner,
    Backend,
):
    """macOS automation via Peekaboo CLI wrapper.

    Delegates all operations to the Peekaboo CLI (``peekaboo``), parsing
    JSON output for structured results. Falls back to helpful error
    messages when Peekaboo is not installed.

    Attributes:
        _peekaboo_path: Resolved path to the peekaboo executable, or None.
    """

    @property
    def platform_name(self) -> str:
        """Return platform identifier."""
        return "macos"

    @property
    def capabilities(self) -> dict:
        """Return backend capabilities."""
        has_peekaboo = self._peekaboo_path is not None
        return {
            "platform": "macos",
            "input_modes": ["normal"],
            "accessibility": ["ax"],
            "extensions": ["dock", "space", "menubar"],
            "peekaboo_available": has_peekaboo,
        }


__all__ = ["MacOSBackend", "PeekabooError"]
