"""Windows backend — powered by naturo_core.dll (C++ engine).

Implements screen capture, window listing, UI element tree inspection,
input simulation, and shell interaction.  Split into focused submodules
for maintainability; the public API is the single ``WindowsBackend`` class.
"""

from __future__ import annotations

from naturo.backends.base import Backend
from naturo.backends.windows._capture import CaptureMixin
from naturo.backends.windows._core import CoreMixin
from naturo.backends.windows._element import ElementMixin
from naturo.backends.windows._input import InputMixin
from naturo.backends.windows._shell import ShellMixin
from naturo.backends.windows._window import WindowMixin

# Re-export names that were previously importable from the monolithic module.
# Tests and external code may patch these at 'naturo.backends.windows.<name>'.
from naturo.bridge import NaturoCore, populate_hierarchy  # noqa: F401


class WindowsBackend(
    ShellMixin,
    InputMixin,
    ElementMixin,
    WindowMixin,
    CaptureMixin,
    CoreMixin,
    Backend,
):
    """Windows automation via naturo_core.dll.

    Uses GDI for screen capture, Win32 API for window management,
    and UIAutomation COM for element inspection.

    Attributes:
        _core: Lazily loaded NaturoCore bridge instance.
        _initialized: Whether naturo_init() has been called.
    """


__all__ = ["WindowsBackend"]
