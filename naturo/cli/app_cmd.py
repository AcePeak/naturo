"""CLI app command extensions — launch, quit, relaunch, list, find, inspect, and window ops.

Replaces the stub implementations in system.py with working process management.
These are registered as subcommands of the existing ``app`` group.
Window operations (focus, close, minimize, maximize, restore, move, resize) are
also registered here, unifying app + window into a single namespace.
"""
import json
import os

from naturo.cli.error_helpers import json_error as _json_error_str
import sys
import click


def _match_windows(windows, name_lower):
    """Match windows by name, excluding the calling process and prioritizing process name.

    Returns a list of matching windows sorted so that process-name matches
    come before title-only matches.  The calling process (own PID and its
    parent, to cover the terminal hosting the command) is excluded so that
    ``naturo app switch feishu`` doesn't accidentally match the terminal
    whose title contains the typed command.

    Args:
        windows: Iterable of window info objects with ``.process_name``,
            ``.title``, and ``.pid`` attributes.
        name_lower: Lowercased search term.

    Returns:
        List of matching windows (process-name matches first, then
        title-only matches), excluding windows owned by this process.
    """
    own_pid = os.getpid()
    parent_pid = os.getppid()

    process_matches = []
    title_matches = []
    for w in windows:
        if w.pid in (own_pid, parent_pid):
            continue
        if name_lower in w.process_name.lower():
            process_matches.append(w)
        elif name_lower in w.title.lower():
            title_matches.append(w)
    return process_matches + title_matches


def _safe_echo(text: str, **kwargs) -> None:
    """Echo text safely, replacing unencodable characters on Windows GBK terminals."""
    try:
        click.echo(text, **kwargs)
    except UnicodeEncodeError:
        # Fallback: encode with replace for terminals that can't handle the chars
        encoded = text.encode(sys.stdout.encoding or "utf-8", errors="replace")
        click.echo(encoded.decode(sys.stdout.encoding or "utf-8", errors="replace"), **kwargs)


@click.command("launch")
@click.argument("name")
@click.option("--path", help="Explicit executable path")
@click.option("--wait-until-ready", is_flag=True, help="Wait for app to create a window")
@click.option("--timeout", type=float, default=30.0, help="Timeout for wait-until-ready")
@click.option("--no-focus", is_flag=True, help="Launch without focusing")
@click.option("--args", multiple=True, help="Arguments to pass to the application")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_launch(ctx, name, path, wait_until_ready, timeout, no_focus, args, json_output):
    """Launch an application by name or path."""
    json_output = json_output or (ctx.obj or {}).get("json", False)

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
            click.echo(json.dumps({
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
            click.echo(json.dumps(exc.to_json_response(), indent=2))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@click.command("quit")
@click.argument("name", required=False, default=None)
@click.option("--name", "name_option", hidden=True, help="Application name (deprecated, use positional)")
@click.option("--pid", type=int, help="Process ID")
@click.option("--force", is_flag=True, help="Force kill immediately")
@click.option("--timeout", type=float, default=10.0, help="Graceful shutdown timeout")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_quit(ctx, name, name_option, pid, force, timeout, json_output):
    """Quit an application gracefully (or force kill).

    NAME is the application name to quit.

    \b
    Examples:
      naturo app quit notepad
      naturo app quit chrome --force
      naturo app quit --pid 12345
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    # Support --name for backward compatibility
    if not name and name_option:
        name = name_option

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
            click.echo(json.dumps({"success": True, "message": f"Quit {name or pid}"}))
        else:
            _safe_echo(f"Quit {name or pid}")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response(), indent=2))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@click.command("relaunch")
@click.argument("name")
@click.option("--wait-until-ready", is_flag=True, default=True, help="Wait for app (default: on)")
@click.option("--timeout", type=float, default=30.0, help="Timeout in seconds")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_relaunch(ctx, name, wait_until_ready, timeout, json_output):
    """Quit and relaunch an application."""
    json_output = json_output or (ctx.obj or {}).get("json", False)

    from naturo.process import relaunch_app
    from naturo.errors import NaturoError

    try:
        info = relaunch_app(name=name, wait_until_ready=wait_until_ready, timeout=timeout)
        if json_output:
            click.echo(json.dumps({
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
            click.echo(json.dumps(exc.to_json_response(), indent=2))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@click.command("list")
@click.option("--all", "show_all", is_flag=True, help="Show all processes (not just apps with windows)")
@click.option("--windows", "show_windows", is_flag=True, help="Show all open windows with details")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_list(ctx, show_all, show_windows, json_output):
    """List running applications with visible windows.

    By default, only user-facing applications with visible windows are shown.
    Use --all to include all processes (system services, background tasks).
    Use --windows to list all open windows with handles and dimensions.
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    if show_windows:
        # Detailed window listing (replaces `naturo window list`)
        from naturo.errors import NaturoError
        try:
            from naturo.backends.base import get_backend
            backend = get_backend()
            windows = backend.list_windows()
        except Exception as exc:
            if json_output:
                click.echo(_json_error_str("BACKEND_ERROR", str(exc)))
            else:
                _safe_echo(f"Error: {exc}", err=True)
            sys.exit(1)
            return

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
        return

    if show_all:
        # Legacy behavior: list all processes via tasklist/ps
        from naturo.process import list_apps as list_all_processes
        apps = list_all_processes()
        if json_output:
            click.echo(json.dumps({
                "success": True,
                "apps": [
                    {"pid": a.pid, "name": a.name, "path": a.path, "is_running": a.is_running}
                    for a in apps
                ],
                "count": len(apps),
            }, indent=2))
        else:
            if not apps:
                click.echo("No running processes found")
            else:
                for a in apps:
                    _safe_echo(f"  {a.pid:>8}  {a.name}")
                click.echo(f"\n{len(apps)} processes")
        return

    # Default: only apps with visible windows (via backend)
    from naturo.errors import NaturoError
    try:
        from naturo.backends.base import get_backend
        backend = get_backend()
        apps_data = backend.list_apps()
    except Exception as exc:
        if json_output:
            click.echo(_json_error_str("BACKEND_ERROR", str(exc)))
        else:
            _safe_echo(f"Error: {exc}", err=True)
        sys.exit(1)
        return

    if json_output:
        click.echo(json.dumps({
            "success": True,
            "apps": apps_data,
            "count": len(apps_data),
        }, indent=2))
    else:
        if not apps_data:
            click.echo("No running applications with visible windows found")
        else:
            for a in apps_data:
                pid = a.get("pid", "")
                name = a.get("name", "")
                title = a.get("title", "")
                path = a.get("process", a.get("path", ""))
                _safe_echo(f"  {pid:>8}  {name:<30} {title}")
            click.echo(f"\n{len(apps_data)} applications")


@click.command("hide", hidden=True)
@click.argument("name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_hide(ctx, name, json_output):
    """Hide (minimize) all windows of an application. Alias for minimize."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
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
            except Exception:
                pass
        if json_output:
            click.echo(json.dumps({"success": True, "action": "hide", "app": name, "windows_minimized": count}))
        else:
            _safe_echo(f"Minimized {count} window(s) of {name}")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@click.command("unhide", hidden=True)
@click.argument("name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_unhide(ctx, name, json_output):
    """Unhide (restore) all windows of an application. Alias for restore."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
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
            except Exception:
                pass
        if json_output:
            click.echo(json.dumps({"success": True, "action": "unhide", "app": name, "windows_restored": count}))
        else:
            _safe_echo(f"Restored {count} window(s) of {name}")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@click.command("switch", hidden=True)
@click.argument("name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_switch(ctx, name, json_output):
    """Switch to (focus) the most recent window of an application. Alias for focus."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
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
            click.echo(json.dumps({"success": True, "action": "switch", "app": name, "window_title": target.title, "handle": target.handle}))
        else:
            _safe_echo(f"Switched to {name}: {target.title}")
    except NaturoError as exc:
        if json_output:
            click.echo(json.dumps(exc.to_json_response()))
        else:
            _safe_echo(f"Error: {exc.message}", err=True)
        sys.exit(1)


@click.command("find")
@click.argument("name")
@click.option("--pid", type=int, help="Search by PID instead of name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_find(ctx, name, pid, json_output):
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

    from naturo.process import find_process

    proc = find_process(name=name, pid=pid)
    if proc:
        if json_output:
            click.echo(json.dumps({
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
            click.echo(json.dumps({
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


@click.command("inspect")
@click.argument("name", required=False, default=None)
@click.option("--pid", type=int, help="Inspect by process ID")
@click.option("--all", "scan_all", is_flag=True, help="Scan all visible windows")
@click.option("--quick", is_flag=True, help="Fast probe — stop at first available method")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_inspect(ctx, name, pid, scan_all, quick, json_output):
    """Probe an application and report available interaction methods.

    Detects which UI framework the app uses (Electron, WPF, Qt, etc.)
    and which interaction methods are available (CDP, UIA, MSAA, JAB, IA2, Vision).

    \b
    Examples:
      naturo app inspect notepad
      naturo app inspect --pid 12345
      naturo app inspect --all
      naturo app inspect chrome --quick --json
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    from naturo.detect import detect, DetectionResult
    from naturo.detect.models import ProbeStatus

    if scan_all:
        _inspect_all_windows(quick, json_output)
        return

    if not name and pid is None:
        msg = "Specify application name, --pid, or --all"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return

    # Validate PID if provided directly
    if pid is not None:
        if pid <= 0:
            msg = f"Invalid PID: {pid}. PID must be a positive integer."
            if json_output:
                click.echo(_json_error_str("INVALID_INPUT", msg))
            else:
                _safe_echo(f"Error: {msg}", err=True)
            sys.exit(1)
            return
        # Check if process actually exists
        from naturo.process import find_process as _find_proc
        if _find_proc(pid=pid) is None:
            msg = f"No process found with PID {pid}. The process may have exited."
            if json_output:
                click.echo(_json_error_str("PROCESS_NOT_FOUND", msg))
            else:
                _safe_echo(f"Error: {msg}", err=True)
            sys.exit(1)
            return

    # Resolve PID from name
    target_pid = pid
    target_exe = ""
    target_name = name or ""

    if name and not pid:
        from naturo.process import find_process
        proc = find_process(name=name)
        if not proc:
            msg = f"No running process found matching '{name}'"
            if json_output:
                click.echo(_json_error_str("PROCESS_NOT_FOUND", msg))
            else:
                _safe_echo(f"Error: {msg}", err=True)
            sys.exit(1)
            return
        target_pid = proc.pid
        target_exe = proc.path or ""
        target_name = proc.name or name

    result = detect(
        pid=target_pid,
        exe=target_exe,
        app_name=target_name,
        use_cache=True,
        quick=quick,
    )

    if json_output:
        click.echo(json.dumps({"success": True, **result.to_dict()}, indent=2))
    else:
        _print_inspect_result(result)


def _inspect_all_windows(quick: bool, json_output: bool) -> None:
    """Scan all visible windows and report detection results.

    Uses (PID, window title) as the deduplication key instead of PID alone.
    This ensures UWP apps hosted by the same ApplicationFrameHost.exe process
    are inspected individually rather than collapsed into a single entry (#252).

    Args:
        quick: If True, use quick probe mode.
        json_output: If True, output as JSON.
    """
    from naturo.detect import detect

    try:
        from naturo.backends.base import get_backend
        backend = get_backend()
        windows = backend.list_windows()
    except Exception as exc:
        if json_output:
            click.echo(_json_error_str("BACKEND_ERROR", str(exc)))
        else:
            _safe_echo(f"Error: {exc}", err=True)
        sys.exit(1)
        return

    results = []
    seen_keys = set()

    for w in windows:
        if not w.is_visible or w.is_minimized:
            continue
        # Deduplicate by (PID, title) to keep distinct UWP windows (#252)
        key = (w.pid, w.title)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        result = detect(
            pid=w.pid,
            exe=w.process_name,
            hwnd=w.handle,
            app_name=w.title or w.process_name,
            use_cache=False,  # Different windows may have different results
            quick=quick,
        )
        results.append(result)

    if json_output:
        click.echo(json.dumps({
            "success": True,
            "apps": [r.to_dict() for r in results],
            "count": len(results),
        }, indent=2))
    else:
        if not results:
            click.echo("No visible applications found")
            return
        for i, result in enumerate(results):
            if i > 0:
                click.echo("")
            _print_inspect_result(result)
        click.echo(f"\n{len(results)} applications scanned")


def _print_inspect_result(result) -> None:
    """Pretty-print a DetectionResult to the terminal.

    Args:
        result: DetectionResult to display.
    """
    from naturo.detect.models import ProbeStatus

    header = f"{result.app_name or result.exe or 'Unknown'} (PID: {result.pid})"
    _safe_echo(f"  {header}")
    _safe_echo(f"  {'─' * len(header)}")

    # Frameworks
    if result.frameworks:
        fw_names = [f.framework_type.value for f in result.frameworks]
        _safe_echo(f"  Framework:  {', '.join(fw_names)}")

    # Methods
    if result.methods:
        for m in result.methods:
            status_icon = {
                ProbeStatus.AVAILABLE: "✅",
                ProbeStatus.FALLBACK: "🔄",
                ProbeStatus.UNAVAILABLE: "❌",
                ProbeStatus.ERROR: "⚠️",
                ProbeStatus.SKIPPED: "⏭️",
            }.get(m.status, "?")

            rec_marker = " ← recommended" if result.recommended == m.method else ""
            caps = ", ".join(m.capabilities) if m.capabilities else ""
            _safe_echo(f"  {status_icon} {m.method.value:<8} ({m.status.value}){rec_marker}")
            if caps:
                _safe_echo(f"             capabilities: {caps}")
            if m.metadata:
                for key, val in m.metadata.items():
                    _safe_echo(f"             {key}: {val}")
    else:
        _safe_echo("  No interaction methods detected")


# ── Window operations (unified under app) ────────────────────────────────────

def _resolve_window_target(name, window_title=None, hwnd=None):
    """Build keyword arguments for backend window methods.

    Accepts the unified app command style: positional NAME with optional
    --window title filter and --hwnd.

    Args:
        name: Application/process name (positional).
        window_title: Optional title substring to pick a specific window.
        hwnd: Optional direct window handle.

    Returns:
        Dict with title and/or hwnd keys for backend calls.
    """
    effective_title = name
    if window_title:
        effective_title = window_title
    return {"title": effective_title, "hwnd": hwnd}


def _require_target(name, window_title, hwnd, json_output):
    """Validate that at least one target identifier is provided.

    Returns:
        True if valid, False if error was emitted.
    """
    if not name and not window_title and not hwnd:
        msg = "Specify an app name, --window, or --hwnd"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return False
    return True


def _handle_naturo_error(exc, json_output):
    """Emit a NaturoError and exit."""
    if json_output:
        click.echo(json.dumps(exc.to_json_response()))
    else:
        _safe_echo(f"Error: {exc.message}", err=True)
    sys.exit(1)


def _handle_generic_error(exc, json_output):
    """Emit a generic exception and exit."""
    if json_output:
        click.echo(_json_error_str("UNKNOWN_ERROR", str(exc)))
    else:
        _safe_echo(f"Error: {exc}", err=True)
    sys.exit(1)


@click.command("focus")
@click.argument("name", required=False, default=None)
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_focus(ctx, name, window_title, hwnd, json_output):
    """Focus an application window (bring to foreground).

    \b
    Examples:
      naturo app focus feishu
      naturo app focus feishu --window "群聊"
      naturo app focus --hwnd 12345
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.errors import NaturoError

    if not _require_target(name, window_title, hwnd, json_output):
        return

    try:
        from naturo.backends.base import get_backend
        backend = get_backend()
        backend.focus_window(**_resolve_window_target(name, window_title, hwnd))
        if json_output:
            click.echo(json.dumps({"success": True, "action": "focus"}))
        else:
            _safe_echo(f"Focused window: {name or window_title or hwnd}")
    except NaturoError as exc:
        _handle_naturo_error(exc, json_output)
    except Exception as exc:
        _handle_generic_error(exc, json_output)


@click.command("close")
@click.argument("name", required=False, default=None)
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--force", is_flag=True, help="Force terminate the process")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_close(ctx, name, window_title, hwnd, force, json_output):
    """Close an application window (graceful or forced).

    \b
    Examples:
      naturo app close notepad
      naturo app close feishu --window "群聊"
      naturo app close --hwnd 12345 --force
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)
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
            click.echo(json.dumps({"success": True, "action": "close", "force": force}))
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
def app_minimize(ctx, name, window_title, hwnd, json_output):
    """Minimize an application window.

    \b
    Examples:
      naturo app minimize feishu
      naturo app minimize --hwnd 12345
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.errors import NaturoError

    if not _require_target(name, window_title, hwnd, json_output):
        return

    try:
        from naturo.backends.base import get_backend
        backend = get_backend()
        backend.minimize_window(**_resolve_window_target(name, window_title, hwnd))
        if json_output:
            click.echo(json.dumps({"success": True, "action": "minimize"}))
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
def app_maximize(ctx, name, window_title, hwnd, json_output):
    """Maximize an application window.

    \b
    Examples:
      naturo app maximize feishu
      naturo app maximize --hwnd 12345
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.errors import NaturoError

    if not _require_target(name, window_title, hwnd, json_output):
        return

    try:
        from naturo.backends.base import get_backend
        backend = get_backend()
        backend.maximize_window(**_resolve_window_target(name, window_title, hwnd))
        if json_output:
            click.echo(json.dumps({"success": True, "action": "maximize"}))
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
def app_restore(ctx, name, window_title, hwnd, json_output):
    """Restore a minimized or maximized window to normal state.

    \b
    Examples:
      naturo app restore feishu
      naturo app restore --hwnd 12345
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.errors import NaturoError

    if not _require_target(name, window_title, hwnd, json_output):
        return

    try:
        from naturo.backends.base import get_backend
        backend = get_backend()
        backend.restore_window(**_resolve_window_target(name, window_title, hwnd))
        if json_output:
            click.echo(json.dumps({"success": True, "action": "restore"}))
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
def app_move(ctx, name, window_title, hwnd, x, y, width, height, json_output):
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
            click.echo(json.dumps(result_data))
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
def app_windows(ctx, name, pid, json_output):
    """List open windows (optionally filtered by app name or PID).

    \b
    Examples:
      naturo app windows
      naturo app windows feishu
      naturo app windows --pid 1234
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)
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
        _handle_naturo_error(exc, json_output)
    except Exception as exc:
        _handle_generic_error(exc, json_output)
