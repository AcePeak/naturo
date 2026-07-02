"""Legacy hidden commands — hide, unhide, switch (backward compatibility)."""
from __future__ import annotations

from naturo.cli._jsonio import json_dumps
import logging
import sys

import click

from naturo.cli.error_helpers import json_error as _json_error_str
from naturo.cli._app._common import (
    _match_windows,
    _resolve_app_id,
    _safe_echo,
)

logger = logging.getLogger(__name__)


@click.command("hide", hidden=True)
@click.argument("name", required=False, default=None)
@click.option("--app", "app_name", default=None, help="Application name (alternative to positional NAME)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_hide(ctx, name, app_name, json_output) -> None:
    """Hide (minimize) all windows of an application. Alias for minimize."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    if not name and app_name:
        name = app_name

    # (#776) Resolve app ID (a1, a2, …) to process name
    entry = _resolve_app_id(name, json_output)
    if entry is False:
        sys.exit(1)
        return
    if entry is not None:
        name = entry.process_name

    if not name:
        msg = "Specify application name"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    try:
        backend = get_backend()
        windows = backend.list_windows()
        name_lower = name.lower()
        matched = _match_windows(windows, name_lower)
        if not matched:
            from naturo.errors import AppNotFoundError
            raise AppNotFoundError(name)
        count = 0
        for w in matched:
            try:
                backend.minimize_window(hwnd=w.handle)
                count += 1
            except Exception as exc:
                logger.debug("Failed to minimize window %s: %s", w.handle, exc)
        if json_output:
            click.echo(json_dumps({"success": True, "action": "hide", "app": name, "windows_minimized": count}))
        else:
            _safe_echo(f"Minimized {count} window(s) of {name}")
    except NaturoError as exc:
        if json_output:
            click.echo(json_dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@click.command("unhide", hidden=True)
@click.argument("name", required=False, default=None)
@click.option("--app", "app_name", default=None, help="Application name (alternative to positional NAME)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_unhide(ctx, name, app_name, json_output) -> None:
    """Unhide (restore) all windows of an application. Alias for restore."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    if not name and app_name:
        name = app_name

    # (#776) Resolve app ID (a1, a2, …) to process name
    entry = _resolve_app_id(name, json_output)
    if entry is False:
        sys.exit(1)
        return
    if entry is not None:
        name = entry.process_name

    if not name:
        msg = "Specify application name"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    try:
        backend = get_backend()
        windows = backend.list_windows()
        name_lower = name.lower()
        matched = _match_windows(windows, name_lower)
        if not matched:
            from naturo.errors import AppNotFoundError
            raise AppNotFoundError(name)
        count = 0
        for w in matched:
            try:
                backend.restore_window(hwnd=w.handle)
                count += 1
            except Exception as exc:
                logger.debug("Failed to restore window %s: %s", w.handle, exc)
        if json_output:
            click.echo(json_dumps({"success": True, "action": "unhide", "app": name, "windows_restored": count}))
        else:
            _safe_echo(f"Restored {count} window(s) of {name}")
    except NaturoError as exc:
        if json_output:
            click.echo(json_dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@click.command("switch", hidden=True)
@click.argument("name", required=False, default=None)
@click.option("--app", "app_name", default=None, help="Application name (alternative to positional NAME)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_switch(ctx, name, app_name, json_output) -> None:
    """Switch to (focus) the most recent window of an application. Alias for focus."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    if not name and app_name:
        name = app_name

    # (#776) Resolve app ID (a1, a2, …) to process name
    entry = _resolve_app_id(name, json_output)
    if entry is False:
        sys.exit(1)
        return
    if entry is not None:
        name = entry.process_name

    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    try:
        backend = get_backend()
        windows = backend.list_windows()
        name_lower = name.lower()
        matched = _match_windows(windows, name_lower)
        if not matched:
            from naturo.errors import AppNotFoundError
            raise AppNotFoundError(name)
        # Focus the first (most recent) matching window
        target = matched[0]
        backend.focus_window(hwnd=target.handle)
        if json_output:
            click.echo(json_dumps({"success": True, "action": "switch", "app": name, "window_title": target.title, "handle": target.handle}))
        else:
            _safe_echo(f"Switched to {name}: {target.title}")
    except NaturoError as exc:
        if json_output:
            click.echo(json_dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)
