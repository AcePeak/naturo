"""Window state management — focus, close, minimize, maximize, restore, move, windows."""
from __future__ import annotations

from naturo.cli._jsonio import json_dumps
import sys

import click

from naturo.cli.error_helpers import json_error as _json_error_str
from naturo.cli.core._common import _enforce_desktop_session
from naturo.cli._app._common import (
    _handle_generic_error,
    _handle_naturo_error,
    _require_target,
    _resolve_app_id,
    _resolve_window_target,
    _safe_echo,
)


@click.command("focus")
@click.argument("name", required=False, default=None)
@click.option("--app", "app_name", default=None, help="Application name (alternative to positional NAME)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_focus(ctx, name, app_name, window_title, hwnd, json_output) -> None:
    """Focus an application window (bring to foreground).

    \b
    Examples:
      naturo app focus feishu
      naturo app focus --app feishu
      naturo app focus feishu --window "Chat"
      naturo app focus --app feishu
      naturo app focus --hwnd 12345
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)
    # --app flag overrides positional NAME when both absent
    if not name and app_name:
        name = app_name

    # (#776) Resolve app ID (a1, a2, …) to window handle
    entry = _resolve_app_id(name, json_output)
    if entry is False:
        sys.exit(1)
        return
    if entry is not None:
        hwnd = entry.handle
        name = None

    from naturo.errors import NaturoError

    if not _require_target(name, window_title, hwnd, json_output):
        return

    try:
        from naturo.backends.base import get_backend
        backend = get_backend()
        backend.focus_window(**_resolve_window_target(name, window_title, hwnd))
        if json_output:
            click.echo(json_dumps({"success": True, "action": "focus"}))
        else:
            _safe_echo(f"Focused window: {name or window_title or hwnd}")
    except NaturoError as exc:
        _handle_naturo_error(exc, json_output)
    except Exception as exc:
        _handle_generic_error(exc, json_output)


@click.command("close")
@click.argument("name", required=False, default=None)
@click.option("--app", "app_name", default=None, help="Application name (alternative to positional NAME)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--force", is_flag=True, help="Force terminate the process")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_close(ctx, name, app_name, window_title, hwnd, force, json_output) -> None:
    """Close an application window (graceful or forced).

    \b
    Examples:
      naturo app close notepad
      naturo app close --app notepad
      naturo app close feishu --window "Chat"
      naturo app close --hwnd 12345 --force
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)
    if not name and app_name:
        name = app_name

    # (#776) Resolve app ID (a1, a2, …) to window handle
    entry = _resolve_app_id(name, json_output)
    if entry is False:
        sys.exit(1)
        return
    if entry is not None:
        hwnd = entry.handle
        name = None

    from naturo.errors import NaturoError

    if not _require_target(name, window_title, hwnd, json_output):
        return

    try:
        from naturo.backends.base import get_backend
        backend = get_backend()
        kwargs = _resolve_window_target(name, window_title, hwnd)
        kwargs["force"] = force
        backend.close_window(**kwargs)
        if json_output:
            click.echo(json_dumps({"success": True, "action": "close", "force": force}))
        else:
            _safe_echo(f"Closed window: {name or window_title or hwnd}")
    except NaturoError as exc:
        _handle_naturo_error(exc, json_output)
    except Exception as exc:
        _handle_generic_error(exc, json_output)


@click.command("minimize")
@click.argument("name", required=False, default=None)
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_minimize(ctx, name, window_title, hwnd, json_output) -> None:
    """Minimize an application window.

    \b
    Examples:
      naturo app minimize feishu
      naturo app minimize --hwnd 12345
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    # (#776) Resolve app ID (a1, a2, …) to window handle
    entry = _resolve_app_id(name, json_output)
    if entry is False:
        sys.exit(1)
        return
    if entry is not None:
        hwnd = entry.handle
        name = None

    from naturo.errors import NaturoError

    if not _require_target(name, window_title, hwnd, json_output):
        return

    try:
        from naturo.backends.base import get_backend
        backend = get_backend()
        backend.minimize_window(**_resolve_window_target(name, window_title, hwnd))
        if json_output:
            click.echo(json_dumps({"success": True, "action": "minimize"}))
        else:
            _safe_echo(f"Minimized window: {name or window_title or hwnd}")
    except NaturoError as exc:
        _handle_naturo_error(exc, json_output)
    except Exception as exc:
        _handle_generic_error(exc, json_output)


@click.command("maximize")
@click.argument("name", required=False, default=None)
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_maximize(ctx, name, window_title, hwnd, json_output) -> None:
    """Maximize an application window.

    \b
    Examples:
      naturo app maximize feishu
      naturo app maximize --hwnd 12345
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    # (#776) Resolve app ID (a1, a2, …) to window handle
    entry = _resolve_app_id(name, json_output)
    if entry is False:
        sys.exit(1)
        return
    if entry is not None:
        hwnd = entry.handle
        name = None

    from naturo.errors import NaturoError

    if not _require_target(name, window_title, hwnd, json_output):
        return

    try:
        from naturo.backends.base import get_backend
        backend = get_backend()
        backend.maximize_window(**_resolve_window_target(name, window_title, hwnd))
        if json_output:
            click.echo(json_dumps({"success": True, "action": "maximize"}))
        else:
            _safe_echo(f"Maximized window: {name or window_title or hwnd}")
    except NaturoError as exc:
        _handle_naturo_error(exc, json_output)
    except Exception as exc:
        _handle_generic_error(exc, json_output)


@click.command("restore")
@click.argument("name", required=False, default=None)
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_restore(ctx, name, window_title, hwnd, json_output) -> None:
    """Restore a minimized or maximized window to normal state.

    \b
    Examples:
      naturo app restore feishu
      naturo app restore --hwnd 12345
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    # (#776) Resolve app ID (a1, a2, …) to window handle
    entry = _resolve_app_id(name, json_output)
    if entry is False:
        sys.exit(1)
        return
    if entry is not None:
        hwnd = entry.handle
        name = None

    from naturo.errors import NaturoError

    if not _require_target(name, window_title, hwnd, json_output):
        return

    try:
        from naturo.backends.base import get_backend
        backend = get_backend()
        backend.restore_window(**_resolve_window_target(name, window_title, hwnd))
        if json_output:
            click.echo(json_dumps({"success": True, "action": "restore"}))
        else:
            _safe_echo(f"Restored window: {name or window_title or hwnd}")
    except NaturoError as exc:
        _handle_naturo_error(exc, json_output)
    except Exception as exc:
        _handle_generic_error(exc, json_output)


@click.command("move")
@click.argument("name", required=False, default=None)
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--x", type=int, default=None, help="Target X position")
@click.option("--y", type=int, default=None, help="Target Y position")
@click.option("--width", type=int, default=None, help="New width in pixels (optional)")
@click.option("--height", type=int, default=None, help="New height in pixels (optional)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_move(ctx, name, window_title, hwnd, x, y, width, height, json_output) -> None:
    """Move and/or resize an application window.

    Combines move, resize, and set-bounds into one command.
    Provide --x/--y for position and/or --width/--height for size.

    \b
    Examples:
      naturo app move feishu --x 100 --y 100
      naturo app move feishu --x 100 --y 100 --width 800 --height 600
      naturo app move feishu --width 800 --height 600
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    # (#776) Resolve app ID (a1, a2, …) to window handle
    entry = _resolve_app_id(name, json_output)
    if entry is False:
        sys.exit(1)
        return
    if entry is not None:
        hwnd = entry.handle
        name = None

    from naturo.errors import NaturoError

    if not _require_target(name, window_title, hwnd, json_output):
        return

    has_position = x is not None and y is not None
    has_size = width is not None and height is not None
    has_partial_position = (x is not None) != (y is not None)
    has_partial_size = (width is not None) != (height is not None)

    if has_partial_position:
        msg = "Both --x and --y are required when setting position"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    if has_partial_size:
        msg = "Both --width and --height are required when setting size"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    if not has_position and not has_size:
        msg = "Provide --x/--y for position and/or --width/--height for size"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    if has_size and (width < 1 or height < 1):
        msg = f"Width and height must be >= 1, got width={width} height={height}"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    try:
        from naturo.backends.base import get_backend
        backend = get_backend()
        kwargs = _resolve_window_target(name, window_title, hwnd)

        if has_position and has_size:
            backend.set_bounds(x=x, y=y, width=width, height=height, **kwargs)
            action = "set-bounds"
            result_data = {"success": True, "action": action, "x": x, "y": y, "width": width, "height": height}
            msg = f"Set bounds: ({x}, {y}) {width}x{height}"
        elif has_position:
            backend.move_window(x=x, y=y, **kwargs)
            action = "move"
            result_data = {"success": True, "action": action, "x": x, "y": y}
            msg = f"Moved window to ({x}, {y})"
        else:
            backend.resize_window(width=width, height=height, **kwargs)
            action = "resize"
            result_data = {"success": True, "action": action, "width": width, "height": height}
            msg = f"Resized window to {width}x{height}"

        if json_output:
            click.echo(json_dumps(result_data))
        else:
            _safe_echo(msg)
    except NaturoError as exc:
        _handle_naturo_error(exc, json_output)
    except Exception as exc:
        _handle_generic_error(exc, json_output)


@click.command("windows")
@click.argument("name", required=False, default=None)
@click.option("--pid", type=int, help="Process ID")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_windows(ctx, name, pid, json_output) -> None:
    """List open windows (optionally filtered by app name or PID).

    \b
    Examples:
      naturo app windows
      naturo app windows feishu
      naturo app windows --pid 1234
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    # (#885) Refuse to enumerate windows without a desktop session — otherwise
    # this returns a real window list (bypassing the guard) and silently lies.
    _enforce_desktop_session(json_output)

    # (#776) Resolve app ID (a1, a2, …) to process name/PID for filtering
    entry = _resolve_app_id(name, json_output)
    if entry is False:
        sys.exit(1)
        return
    if entry is not None:
        name = entry.process_name
        if pid is None:
            pid = entry.pid

    from naturo.errors import NaturoError

    try:
        from naturo.backends.base import get_backend
        backend = get_backend()
        windows = backend.list_windows()

        if name:
            name_lower = name.lower()
            windows = [w for w in windows if name_lower in w.process_name.lower() or name_lower in w.title.lower()]
        if pid is not None:
            windows = [w for w in windows if w.pid == pid]

        if json_output:
            click.echo(json_dumps({
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
        _handle_naturo_error(exc, json_output)
    except Exception as exc:
        _handle_generic_error(exc, json_output)
