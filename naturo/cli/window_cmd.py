"""CLI window commands — focus, close, minimize, maximize, restore, move, resize, set-bounds, list.

Provides window management through the ``naturo window`` command group.
Each command targets a window via ``--app``, ``--title``, or ``--hwnd``.
"""
from __future__ import annotations

import json
import sys
from typing import Optional

import click

from naturo.cli.error_helpers import emit_error, emit_exception_error, json_error


def _safe_echo(text: str, **kwargs) -> None:
    """Echo text safely, replacing unencodable characters on Windows GBK terminals.

    Args:
        text: Text to echo.
        **kwargs: Passed through to click.echo.
    """
    try:
        click.echo(text, **kwargs)
    except UnicodeEncodeError:
        encoded = text.encode(sys.stdout.encoding or "utf-8", errors="replace")
        click.echo(encoded.decode(sys.stdout.encoding or "utf-8", errors="replace"), **kwargs)


from naturo.backends.base import get_backend as _get_backend_impl


def _get_backend():
    """Get the platform backend.

    Returns:
        Backend instance for the current platform.
    """
    return _get_backend_impl()


def _resolve_target(app: Optional[str], title: Optional[str], hwnd: Optional[int]) -> dict:
    """Build keyword arguments for backend window methods from CLI targeting options.

    Args:
        app: Application name filter.
        title: Window title filter.
        hwnd: Direct window handle.

    Returns:
        Dict with title and/or hwnd keys for backend calls.
    """
    # --app maps to title parameter in backend (which does partial match on both title and process)
    effective_title = app or title
    return {"title": effective_title, "hwnd": hwnd}


@click.group()
def window():
    """Manage windows: focus, close, minimize, maximize, restore, move, resize."""
    pass


@window.command()
@click.option("--app", help="Application/process name (partial match)")
@click.option("--title", help="Window title pattern (partial match)")
@click.option("--hwnd", type=int, help="Window handle")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def focus(ctx, app, title, hwnd, json_output):
    """Focus a window (bring to foreground)."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.errors import NaturoError

    if not app and not title and not hwnd:
        msg = "Specify --app, --title, or --hwnd"
        if json_output:
            click.echo(json_error("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    try:
        backend = _get_backend()
        backend.focus_window(**_resolve_target(app, title, hwnd))
        if json_output:
            click.echo(json.dumps({"success": True, "action": "focus"}))
        else:
            _safe_echo(f"Focused window: {app or title or hwnd}")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@window.command()
@click.option("--app", help="Application/process name (partial match)")
@click.option("--title", help="Window title pattern (partial match)")
@click.option("--hwnd", type=int, help="Window handle")
@click.option("--force", is_flag=True, help="Force terminate the process")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def close(ctx, app, title, hwnd, force, json_output):
    """Close a window (graceful or forced)."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.errors import NaturoError

    if not app and not title and not hwnd:
        msg = "Specify --app, --title, or --hwnd"
        if json_output:
            click.echo(json_error("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    try:
        backend = _get_backend()
        kwargs = _resolve_target(app, title, hwnd)
        kwargs["force"] = force
        backend.close_window(**kwargs)
        if json_output:
            click.echo(json.dumps({"success": True, "action": "close", "force": force}))
        else:
            _safe_echo(f"Closed window: {app or title or hwnd}")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@window.command()
@click.option("--app", help="Application/process name (partial match)")
@click.option("--title", help="Window title pattern (partial match)")
@click.option("--hwnd", type=int, help="Window handle")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def minimize(ctx, app, title, hwnd, json_output):
    """Minimize a window."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.errors import NaturoError

    if not app and not title and not hwnd:
        msg = "Specify --app, --title, or --hwnd"
        if json_output:
            click.echo(json_error("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    try:
        backend = _get_backend()
        backend.minimize_window(**_resolve_target(app, title, hwnd))
        if json_output:
            click.echo(json.dumps({"success": True, "action": "minimize"}))
        else:
            _safe_echo(f"Minimized window: {app or title or hwnd}")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@window.command()
@click.option("--app", help="Application/process name (partial match)")
@click.option("--title", help="Window title pattern (partial match)")
@click.option("--hwnd", type=int, help="Window handle")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def maximize(ctx, app, title, hwnd, json_output):
    """Maximize a window."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.errors import NaturoError

    if not app and not title and not hwnd:
        msg = "Specify --app, --title, or --hwnd"
        if json_output:
            click.echo(json_error("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    try:
        backend = _get_backend()
        backend.maximize_window(**_resolve_target(app, title, hwnd))
        if json_output:
            click.echo(json.dumps({"success": True, "action": "maximize"}))
        else:
            _safe_echo(f"Maximized window: {app or title or hwnd}")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@window.command()
@click.option("--app", help="Application/process name (partial match)")
@click.option("--title", help="Window title pattern (partial match)")
@click.option("--hwnd", type=int, help="Window handle")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def restore(ctx, app, title, hwnd, json_output):
    """Restore a minimized or maximized window to normal state."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.errors import NaturoError

    if not app and not title and not hwnd:
        msg = "Specify --app, --title, or --hwnd"
        if json_output:
            click.echo(json_error("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    try:
        backend = _get_backend()
        backend.restore_window(**_resolve_target(app, title, hwnd))
        if json_output:
            click.echo(json.dumps({"success": True, "action": "restore"}))
        else:
            _safe_echo(f"Restored window: {app or title or hwnd}")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@window.command(name="move")
@click.option("--app", help="Application/process name (partial match)")
@click.option("--title", help="Window title pattern (partial match)")
@click.option("--hwnd", type=int, help="Window handle")
@click.option("--x", type=int, default=None, help="Target X position")
@click.option("--y", type=int, default=None, help="Target Y position")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def window_move(ctx, app, title, hwnd, x, y, json_output):
    """Move a window to a position (keeps current size)."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.errors import NaturoError

    if x is None or y is None:
        msg = "Missing required option: --x and --y are required"
        if json_output:
            click.echo(json_error("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)

    if not app and not title and not hwnd:
        msg = "Specify --app, --title, or --hwnd"
        if json_output:
            click.echo(json_error("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    try:
        backend = _get_backend()
        kwargs = _resolve_target(app, title, hwnd)
        backend.move_window(x=x, y=y, **kwargs)
        if json_output:
            click.echo(json.dumps({"success": True, "action": "move", "x": x, "y": y}))
        else:
            _safe_echo(f"Moved window to ({x}, {y})")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@window.command()
@click.option("--app", help="Application/process name (partial match)")
@click.option("--title", help="Window title pattern (partial match)")
@click.option("--hwnd", type=int, help="Window handle")
@click.option("--width", type=int, default=None, help="New width in pixels")
@click.option("--height", type=int, default=None, help="New height in pixels")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def resize(ctx, app, title, hwnd, width, height, json_output):
    """Resize a window (keeps current position)."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.errors import NaturoError, InvalidInputError

    if width is None or height is None:
        msg = "Missing required option: --width and --height are required"
        if json_output:
            click.echo(json_error("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)

    if not app and not title and not hwnd:
        msg = "Specify --app, --title, or --hwnd"
        if json_output:
            click.echo(json_error("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    if width < 1 or height < 1:
        msg = f"Width and height must be >= 1, got width={width} height={height}"
        if json_output:
            click.echo(json_error("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    try:
        backend = _get_backend()
        kwargs = _resolve_target(app, title, hwnd)
        backend.resize_window(width=width, height=height, **kwargs)
        if json_output:
            click.echo(json.dumps({"success": True, "action": "resize", "width": width, "height": height}))
        else:
            _safe_echo(f"Resized window to {width}x{height}")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@window.command(name="set-bounds")
@click.option("--app", help="Application/process name (partial match)")
@click.option("--title", help="Window title pattern (partial match)")
@click.option("--hwnd", type=int, help="Window handle")
@click.option("--x", type=int, default=None, help="X position")
@click.option("--y", type=int, default=None, help="Y position")
@click.option("--width", type=int, default=None, help="Width in pixels")
@click.option("--height", type=int, default=None, help="Height in pixels")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def set_bounds(ctx, app, title, hwnd, x, y, width, height, json_output):
    """Set window position and size at once."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.errors import NaturoError

    missing = []
    if x is None:
        missing.append("--x")
    if y is None:
        missing.append("--y")
    if width is None:
        missing.append("--width")
    if height is None:
        missing.append("--height")
    if missing:
        msg = f"Missing required option(s): {', '.join(missing)}"
        if json_output:
            click.echo(json_error("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)

    if not app and not title and not hwnd:
        msg = "Specify --app, --title, or --hwnd"
        if json_output:
            click.echo(json_error("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    if width < 1 or height < 1:
        msg = f"Width and height must be >= 1, got width={width} height={height}"
        if json_output:
            click.echo(json_error("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    try:
        backend = _get_backend()
        kwargs = _resolve_target(app, title, hwnd)
        backend.set_bounds(x=x, y=y, width=width, height=height, **kwargs)
        if json_output:
            click.echo(json.dumps({"success": True, "action": "set-bounds", "x": x, "y": y, "width": width, "height": height}))
        else:
            _safe_echo(f"Set bounds: ({x}, {y}) {width}x{height}")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@window.command(name="list")
@click.option("--app", help="Filter by application/process name")
@click.option("--process-name", help="Filter by process name")
@click.option("--pid", type=int, help="Filter by process ID")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def window_list(ctx, app, process_name, pid, json_output):
    """List open windows."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.errors import NaturoError

    try:
        backend = _get_backend()
        windows = backend.list_windows()

        # Apply filters
        if app:
            app_lower = app.lower()
            windows = [w for w in windows if app_lower in w.process_name.lower() or app_lower in w.title.lower()]
        if process_name:
            pn_lower = process_name.lower()
            windows = [w for w in windows if pn_lower in w.process_name.lower()]
        if pid is not None:
            windows = [w for w in windows if w.pid == pid]

        if json_output:
            click.echo(json.dumps({
                "success": True,
                "windows": [
                    {
                        "handle": w.handle,
                        "title": w.title,
                        "process_name": w.process_name,
                        "pid": w.pid,
                        "x": w.x, "y": w.y,
                        "width": w.width, "height": w.height,
                        "is_visible": w.is_visible,
                        "is_minimized": w.is_minimized,
                    }
                    for w in windows
                ],
                "count": len(windows),
            }, indent=2))
        else:
            if not windows:
                click.echo("No windows found")
            else:
                for w in windows:
                    _safe_echo(f"  {w.handle:>10}  {w.process_name:<20}  {w.title}")
                click.echo(f"\n{len(windows)} windows")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)
