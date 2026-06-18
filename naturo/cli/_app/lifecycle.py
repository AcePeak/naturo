"""App lifecycle commands — launch, quit, relaunch, list, find."""
from __future__ import annotations

from naturo.cli._jsonio import json_dumps
import os
import sys

import click

from naturo.cli.error_helpers import json_error as _json_error_str
from naturo.cli._app._common import (
    _APP_ID_RE,
    _resolve_app_id,
    _safe_echo,
)


@click.command("launch")
@click.argument("name", required=False, default=None)
@click.option("--app", "app_name", default=None, help="Application name (alternative to positional NAME)")
@click.option("--path", help="Explicit executable path")
@click.option("--wait-until-ready", is_flag=True, help="Wait for app to create a window")
@click.option("--timeout", type=float, default=30.0, help="Timeout for wait-until-ready")
@click.option("--no-focus", is_flag=True, help="Launch without focusing")
@click.option("--args", multiple=True, help="Arguments to pass to the application")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_launch(ctx, name, app_name, path, wait_until_ready, timeout, no_focus, args, json_output) -> None:
    """Launch an application by name or path."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    if not name and app_name:
        name = app_name
    if not name and not path:
        msg = "Specify application name or --path"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    # (#776) Reject app IDs — launch requires an app name/path, not a running-app ID
    if name and _APP_ID_RE.fullmatch(name):
        msg = f'Cannot launch by app ID "{name}". Use an app name or --path instead.'
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    from naturo.process import launch_app
    from naturo.errors import NaturoError

    try:
        info = launch_app(
            name=name,
            path=path,
            wait_until_ready=wait_until_ready,
            timeout=timeout,
            args=list(args) if args else None,
            no_focus=no_focus,
        )
        if json_output:
            click.echo(json_dumps({
                "success": True,
                "process": {
                    "pid": info.pid,
                    "name": info.name,
                    "path": info.path,
                    "is_running": info.is_running,
                    "window_count": info.window_count,
                },
            }, indent=2))
        else:
            _safe_echo(f"Launched {info.name} (PID: {info.pid})")
    except NaturoError as exc:
        if json_output:
            click.echo(json_dumps(exc.to_json_response(), indent=2))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@click.command("quit")
@click.argument("name", required=False, default=None)
@click.option("--name", "name_option", hidden=True, help="Application name (deprecated, use positional)")
@click.option("--app", "app_name", default=None, help="Application name (alternative to positional NAME)")
@click.option("--pid", type=int, help="Process ID")
@click.option("--force", is_flag=True, help="Force kill immediately")
@click.option("--timeout", type=float, default=10.0, help="Graceful shutdown timeout")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_quit(ctx, name, name_option, app_name, pid, force, timeout, json_output) -> None:
    """Quit an application gracefully (or force kill).

    NAME is the application name to quit.

    \b
    Examples:
      naturo app quit notepad
      naturo app quit chrome --force
      naturo app quit --pid 12345
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    # Support --name for backward compatibility, --app for consistency
    if not name and name_option:
        name = name_option
    if not name and app_name:
        name = app_name

    # (#776) Resolve app ID (a1, a2, …) to process name/PID
    entry = _resolve_app_id(name, json_output)
    if entry is False:
        sys.exit(1)
        return
    if entry is not None:
        name = entry.process_name
        if pid is None:
            pid = entry.pid

    if not name and pid is None:
        msg = "Specify application name or --pid"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    from naturo.process import quit_app
    from naturo.errors import NaturoError

    try:
        quit_app(name=name, pid=pid, force=force, timeout=timeout)
        if json_output:
            click.echo(json_dumps({"success": True, "message": f"Quit {name or pid}"}))
        else:
            _safe_echo(f"Quit {name or pid}")
    except NaturoError as exc:
        if json_output:
            click.echo(json_dumps(exc.to_json_response(), indent=2))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@click.command("relaunch")
@click.argument("name", required=False, default=None)
@click.option("--app", "app_name", default=None, help="Application name (alternative to positional NAME)")
@click.option("--wait-until-ready", is_flag=True, default=True, help="Wait for app (default: on)")
@click.option("--timeout", type=float, default=30.0, help="Timeout in seconds")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_relaunch(ctx, name, app_name, wait_until_ready, timeout, json_output) -> None:
    """Quit and relaunch an application."""
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

    from naturo.process import relaunch_app
    from naturo.errors import NaturoError

    try:
        info = relaunch_app(name=name, wait_until_ready=wait_until_ready, timeout=timeout)
        if json_output:
            click.echo(json_dumps({
                "success": True,
                "process": {
                    "pid": info.pid,
                    "name": info.name,
                    "path": info.path,
                    "is_running": info.is_running,
                    "window_count": info.window_count,
                },
            }, indent=2))
        else:
            _safe_echo(f"Relaunched {info.name} (PID: {info.pid})")
    except NaturoError as exc:
        if json_output:
            click.echo(json_dumps(exc.to_json_response(), indent=2))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@click.command("list")
@click.option("--all", "show_all", is_flag=True, help="Show all processes (not just apps with windows)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_list(ctx, show_all, json_output) -> None:
    """List running applications with visible windows.

    By default, shows user-facing applications with visible windows
    (PID, HWND, process name, and title). Output is compatible with
    the deprecated `naturo window list` command.

    Use --all to include all processes (system services, background tasks).
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    # Default: list windows (replaces backend.list_apps with filtered backend.list_windows)
    # This unifies `app list` and `window list` output formats (#274)
    try:
        # Check for interactive desktop session before listing (#373)
        from naturo.cli.interaction import _check_desktop_session
        try:
            _check_desktop_session()
        except Exception as exc:
            if json_output:
                click.echo(_json_error_str("NO_DESKTOP_SESSION", str(exc)))
            else:
                _safe_echo(f"Error: {exc}", err=True)
            sys.exit(1)
            return

        from naturo.backends.base import get_backend
        backend = get_backend()
        windows = backend.list_windows()

        # Apply same filtering as backend.list_apps:
        # - visible, non-minimized windows
        # - exclude system processes (platform-specific)
        # - exclude empty titles
        # - deduplicate by (PID, title) for UWP apps

        system_processes = set()
        if hasattr(backend, '_SYSTEM_PROCESS_NAMES'):
            system_processes = backend._SYSTEM_PROCESS_NAMES

        # Resolve UWP host process name for ApplicationFrameHost windows
        # so that UWP apps (Notepad, Calculator, Settings) display with
        # their real process name instead of "ApplicationFrameHost.exe" (#749).
        uwp_host = getattr(backend, '_UWP_HOST_PROCESS', 'applicationframehost.exe')
        resolve_uwp = hasattr(backend, '_resolve_uwp_child_pid')

        filtered_windows = []
        seen_keys = set()

        for w in windows:
            if not w.is_visible or w.is_minimized:
                continue
            if not w.title or not w.title.strip():
                continue

            basename = os.path.basename(w.process_name).lower()
            if basename in system_processes:
                continue

            # UWP apps: resolve real child process inside AFH (#749)
            if resolve_uwp and basename == uwp_host:
                real_pid, real_exe = backend._resolve_uwp_child_pid(w.handle)  # type: ignore[attr-defined]
                if real_pid and real_exe:
                    w = type(w)(
                        handle=w.handle,
                        title=w.title,
                        process_name=real_exe,
                        pid=real_pid,
                        x=w.x, y=w.y,
                        width=w.width, height=w.height,
                        is_visible=w.is_visible,
                        is_minimized=w.is_minimized,
                    )

            # Deduplicate by (PID, title) to match backend.list_apps behavior for UWP apps
            key = (w.pid, w.title)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            filtered_windows.append(w)

        windows = filtered_windows

        # Assign stable session-scoped IDs (a1, a2, ...) for --id targeting (#361)
        from naturo.app_ids import get_app_id_map
        id_map = get_app_id_map()
        id_map.assign_ids(windows)

    except Exception as exc:
        if json_output:
            click.echo(_json_error_str("BACKEND_ERROR", str(exc)))
        else:
            _safe_echo(f"Error: {exc}", err=True)
        sys.exit(1)
        return

    # --all: append processes that have no visible windows (#355)
    background_apps = []
    if show_all:
        from naturo.process import list_apps as list_all_processes
        all_procs = list_all_processes()
        window_pids = {w.pid for w in windows}
        background_apps = [a for a in all_procs if a.pid not in window_pids]

    if json_output:
        result = {
            "success": True,
            "windows": [
                {
                    "id": f"a{i}",
                    "handle": w.handle,
                    "pid": w.pid,
                    "process_name": w.process_name,
                    "title": w.title,
                    "x": w.x, "y": w.y,
                    "width": w.width, "height": w.height,
                    "is_visible": w.is_visible,
                    "is_minimized": w.is_minimized,
                }
                for i, w in enumerate(windows, start=1)
            ],
            "count": len(windows),
        }
        if show_all:
            result["background_processes"] = [
                {"pid": a.pid, "name": a.name, "path": a.path}
                for a in background_apps
            ]
            result["total_count"] = len(windows) + len(background_apps)
        click.echo(json_dumps(result, indent=2))
    else:
        from naturo.cli.table import print_table

        if not windows and not background_apps:
            click.echo("No running applications with visible windows found")
        else:
            headers = ["ID", "PID", "HWND", "Process", "Title"]
            rows = []
            for i, w in enumerate(windows, start=1):
                title = w.title[:40] if len(w.title) > 40 else w.title
                rows.append([f"a{i}", str(w.pid), str(w.handle), w.process_name, title])

            if background_apps:
                for a in background_apps:
                    rows.append(["", str(a.pid), "", a.name, "(background)"])

            count_label = (
                f"{len(windows)} applications, {len(background_apps)} background processes"
                if show_all
                else f"{len(windows)} applications"
            )
            print_table(headers, rows, count_label=count_label)


@click.command("find")
@click.argument("name")
@click.option("--pid", type=int, help="Search by PID instead of name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_find(ctx, name, pid, json_output) -> None:
    """Find a running application by name or PID."""
    json_output = json_output or (ctx.obj or {}).get("json", False)

    # Validate empty name
    if not name or not name.strip():
        msg = "Name cannot be empty"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    # (#776) Resolve app ID (a1, a2, …) to process name/PID
    entry = _resolve_app_id(name, json_output)
    if entry is False:
        sys.exit(1)
        return
    if entry is not None:
        name = entry.process_name
        if pid is None:
            pid = entry.pid

    from naturo.process import find_process

    proc = find_process(name=name, pid=pid)
    if proc:
        if json_output:
            click.echo(json_dumps({
                "success": True,
                "process": {
                    "pid": proc.pid,
                    "name": proc.name,
                    "path": proc.path,
                    "is_running": proc.is_running,
                    "window_count": proc.window_count,
                },
            }, indent=2))
        else:
            _safe_echo(f"Found: {proc.name} (PID: {proc.pid})")
    else:
        if json_output:
            click.echo(json_dumps({
                "success": False,
                "process": None,
                "error": {
                    "code": "PROCESS_NOT_FOUND",
                    "message": f"No process found matching '{name}'",
                },
            }, indent=2))
        else:
            _safe_echo(f"Not found: {name}")
        sys.exit(1)
