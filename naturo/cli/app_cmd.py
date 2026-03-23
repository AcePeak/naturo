"""CLI app command extensions — launch, quit, relaunch, list, find, inspect.

Replaces the stub implementations in system.py with working process management.
These are registered as subcommands of the existing ``app`` group.
"""
import json

from naturo.cli.error_helpers import json_error as _json_error_str
import sys
import click


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
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_list(ctx, show_all, json_output):
    """List running applications with visible windows.

    By default, only user-facing applications with visible windows are shown.
    Use --all to include all processes (system services, background tasks).
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

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


@click.command("hide")
@click.argument("name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_hide(ctx, name, json_output):
    """Hide (minimize) all windows of an application."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    try:
        backend = get_backend()
        windows = backend.list_windows()
        name_lower = name.lower()
        matched = [w for w in windows if name_lower in w.process_name.lower() or name_lower in w.title.lower()]
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


@click.command("unhide")
@click.argument("name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_unhide(ctx, name, json_output):
    """Unhide (restore) all windows of an application."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    try:
        backend = get_backend()
        windows = backend.list_windows()
        name_lower = name.lower()
        matched = [w for w in windows if name_lower in w.process_name.lower() or name_lower in w.title.lower()]
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


@click.command("switch")
@click.argument("name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_switch(ctx, name, json_output):
    """Switch to (focus) the most recent window of an application."""
    json_output = json_output or (ctx.obj or {}).get("json", False)
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    try:
        backend = get_backend()
        windows = backend.list_windows()
        name_lower = name.lower()
        matched = [w for w in windows if name_lower in w.process_name.lower() or name_lower in w.title.lower()]
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

    Args:
        quick: If True, use quick probe mode.
        json_output: If True, output as JSON.
    """
    from naturo.detect import detect

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

    results = []
    seen_pids = set()

    for app_info in apps_data:
        app_pid = app_info.get("pid")
        if not app_pid or app_pid in seen_pids:
            continue
        seen_pids.add(app_pid)

        result = detect(
            pid=app_pid,
            exe=app_info.get("process", ""),
            app_name=app_info.get("name", ""),
            use_cache=True,
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
