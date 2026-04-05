"""``naturo app`` CLI subcommands — lifecycle, diagnostics, window ops, and legacy aliases.

Split from the monolithic ``app_cmd.py`` (1,416 lines) into focused modules:

- ``lifecycle`` — launch, quit, relaunch, list, find
- ``diagnostics`` — inspect (detection chain probing)
- ``window_ops`` — focus, close, minimize, maximize, restore, move, windows
- ``legacy`` — hide, unhide, switch (hidden backward-compatibility aliases)
- ``_common`` — shared helpers (app ID resolution, error formatting, etc.)
"""

from naturo.cli._app.lifecycle import (
    app_find,
    app_launch,
    app_list,
    app_quit,
    app_relaunch,
)
from naturo.cli._app.diagnostics import app_inspect
from naturo.cli._app.window_ops import (
    app_close,
    app_focus,
    app_maximize,
    app_minimize,
    app_move,
    app_restore,
    app_windows,
)
from naturo.cli._app.legacy import app_hide, app_switch, app_unhide

# Re-export private helpers that external code imports directly
from naturo.cli._app._common import _match_windows, _resolve_app_id  # noqa: F401

__all__ = [
    "app_launch",
    "app_quit",
    "app_relaunch",
    "app_list",
    "app_find",
    "app_inspect",
    "app_focus",
    "app_close",
    "app_minimize",
    "app_maximize",
    "app_restore",
    "app_move",
    "app_windows",
    "app_hide",
    "app_unhide",
    "app_switch",
]
