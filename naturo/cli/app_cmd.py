"""Backward-compatibility shim — imports from ``naturo.cli._app`` subpackage.

All code has been split into focused modules under ``naturo/cli/_app/``:

- ``lifecycle.py`` — launch, quit, relaunch, list, find
- ``diagnostics.py`` — inspect
- ``window_ops.py`` — focus, close, minimize, maximize, restore, move, windows
- ``legacy.py`` — hide, unhide, switch
- ``_common.py`` — shared helpers

This file re-exports everything so that ``from naturo.cli.app_cmd import X``
continues to work.
"""

from naturo.cli._app import (  # noqa: F401
    app_close,
    app_find,
    app_focus,
    app_hide,
    app_inspect,
    app_launch,
    app_list,
    app_maximize,
    app_minimize,
    app_move,
    app_quit,
    app_relaunch,
    app_restore,
    app_switch,
    app_unhide,
    app_windows,
)
from naturo.cli._app._common import (  # noqa: F401
    _match_windows,
    _resolve_app_id,
)
