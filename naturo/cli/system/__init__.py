"""System commands: clipboard, dialog, desktop, taskbar, tray.

Split into focused submodules for maintainability.  The public API is
re-exported here so that ``from naturo.cli.system import clipboard``
and similar imports continue to work.

Submodules:
    _clipboard  — clipboard get/set/clear/info commands
    _dialog     — dialog detect/accept/dismiss/click/type commands
    _desktop    — virtual desktop list/switch/create/close/move commands
    _taskbar    — taskbar list/click commands
    _tray       — system tray list/click commands
"""
from __future__ import annotations

from naturo.cli.system._clipboard import clipboard  # noqa: F401
from naturo.cli.system._dialog import dialog  # noqa: F401
from naturo.cli.system._desktop import desktop  # noqa: F401
from naturo.cli.system._taskbar import taskbar  # noqa: F401
from naturo.cli.system._tray import tray  # noqa: F401
