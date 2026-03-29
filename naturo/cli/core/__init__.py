"""Core commands: capture, list, see, find, menu-inspect, highlight, learn, tools.

Split into focused submodules for maintainability.  The public API is
re-exported here so that ``from naturo.cli.core import capture``
and similar imports continue to work.

Submodules:
    _common     — shared helpers (backend, platform checks)
    _capture    — capture command
    _list       — list command group (apps, windows, screens, permissions)
    _see        — see command
    _find       — find command + AI find
    _menu       — menu-inspect command
    _learn      — learn command
    _highlight  — highlight command
    _tools      — tools command (hidden)
"""
from __future__ import annotations

# Re-export shared helpers — used by external code and test patches.
from naturo.cli.core._common import (  # noqa: F401
    _get_backend,
    _platform_supports_gui,
    _platform_error_msg,
)

# Re-export command functions — registered in naturo.cli.__init__.
from naturo.cli.core._capture import capture  # noqa: F401
from naturo.cli.core._list import list_cmd  # noqa: F401
from naturo.cli.core._see import see  # noqa: F401
from naturo.cli.core._find import find_cmd, _find_with_ai  # noqa: F401
from naturo.cli.core._menu import menu_inspect  # noqa: F401
from naturo.cli.core._learn import learn  # noqa: F401
from naturo.cli.core._highlight import highlight  # noqa: F401
from naturo.cli.core._tools import tools  # noqa: F401
