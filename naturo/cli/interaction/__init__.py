"""Interaction commands: click, type, press (includes hotkey), scroll, drag, move.

Split into focused submodules for maintainability.  The public API is
re-exported here so that ``from naturo.cli.interaction import click_cmd``
and similar imports continue to work.

Submodules:
    _common  — shared helpers, decorators, constants
    _click   — click command
    _type    — type command
    _press   — press and hotkey commands
    _mouse   — scroll, drag, move commands
"""
from __future__ import annotations

# Re-export shared helpers — used by external code (naturo.cli.core,
# naturo.cli.app_cmd, naturo.process) and test patches.
from naturo.cli.interaction._common import (  # noqa: F401
    VALID_METHODS,
    _VERIFICATION_KEYS,
    _app_id_option,
    _auto_route,
    _check_desktop_session,
    _elementinfo_to_dict,
    _find_element_by_text_fallback,
    _get_backend,
    _is_current_session_interactive,
    _json_err,
    _json_ok,
    _method_option,
    _post_action_see,
    _record_action,
    _resolve_app_id,
    _resolve_selector_target,
    _see_options,
    _selector_option,
    _validate_method,
    _verify_options,
)

# Re-export command functions — registered in naturo.cli.__init__.
from naturo.cli.interaction._click import click_cmd  # noqa: F401
from naturo.cli.interaction._type import type_cmd  # noqa: F401
from naturo.cli.interaction._press import press, hotkey  # noqa: F401
from naturo.cli.interaction._mouse import scroll, drag, move  # noqa: F401
