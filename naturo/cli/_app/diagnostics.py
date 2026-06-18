"""App detection and diagnostics — inspect command."""
from __future__ import annotations

from naturo.cli._jsonio import json_dumps
import sys

import click

from naturo.cli.error_helpers import json_error as _json_error_str
from naturo.cli._app._common import _resolve_app_id, _safe_echo


@click.command("inspect")
@click.argument("name", required=False, default=None)
@click.option("--app", "app_name", default=None, help="Application name (alternative to positional NAME)")
@click.option("--pid", type=int, help="Inspect by process ID")
@click.option("--all", "scan_all", is_flag=True, help="Scan all visible windows")
@click.option("--quick", is_flag=True, help="Fast probe — stop at first available method")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def app_inspect(ctx, name, app_name, pid, scan_all, quick, json_output) -> None:
    """Probe an application and report available interaction methods.

    Detects which UI framework the app uses (Electron, WPF, Qt, etc.)
    and which interaction methods are available (CDP, UIA, MSAA, JAB, IA2, Vision).

    \b
    Examples:
      naturo app inspect notepad
      naturo app inspect --app notepad
      naturo app inspect --pid 12345
      naturo app inspect --all
      naturo app inspect chrome --quick --json
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    # Accept --app as alias for positional NAME (#289)
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

    from naturo.detect import detect

    if scan_all:
        # (#395) Default to quick mode for --all to avoid timeouts
        # with many open windows.  Users can still run individual
        # inspect calls without --quick for full detection.
        _inspect_all_windows(quick=True, json_output=json_output)
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
    target_hwnd = None

    if name and not pid:
        from naturo.process import find_process
        proc = find_process(name=name, require_interactive=True)
        if not proc:
            # Check if the process exists but only in session 0 (#350)
            session0_proc = find_process(name=name)
            if session0_proc:
                msg = (
                    f"Process '{name}' found (PID {session0_proc.pid}) but it is "
                    f"running in a non-interactive session (session 0).  "
                    f"It has no visible windows on the desktop.  "
                    f"Connect via RDP or Console to interact with desktop apps."
                )
                if json_output:
                    click.echo(json_dumps({
                        "success": False,
                        "error": {
                            "code": "NO_DESKTOP_SESSION",
                            "message": msg,
                            "pid": session0_proc.pid,
                            "session": 0,
                        },
                    }, indent=2))
                else:
                    _safe_echo(f"Error: {msg}", err=True)
                sys.exit(1)
                return
            msg = f"No running process found matching '{name}'"
            if json_output:
                click.echo(_json_error_str("PROCESS_NOT_FOUND", msg))
            else:
                _safe_echo(f"Error: {msg}", err=True)
            sys.exit(1)
            return
        target_pid = proc.pid
        target_exe = proc.path or proc.name or ""
        target_name = proc.name or name

    # Resolve hwnd via the backend for accurate UIA probing (#335).
    # UWP apps (Notepad, Calculator, etc.) have their top-level window
    # owned by ApplicationFrameHost.exe, not the app process itself.
    # The backend's _resolve_hwnd handles this correctly via fuzzy
    # matching on process names and window titles.
    try:
        from naturo.backends.base import get_backend
        _backend = get_backend()
        if hasattr(_backend, "_resolve_hwnd"):
            target_hwnd = _backend._resolve_hwnd(app=name or None)
    except Exception:
        pass  # Non-critical: probes will use _find_main_window fallback

    result = detect(
        pid=target_pid,
        exe=target_exe,
        hwnd=target_hwnd,
        app_name=target_name,
        use_cache=True,
        quick=quick,
    )

    if json_output:
        click.echo(json_dumps({"success": True, **result.to_dict()}, indent=2))
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

    # Filter out session 0 (non-interactive) processes (#350).
    # These are invisible on the desktop and produce misleading results.
    import platform as _platform
    _filter_session0 = False
    _console_session = -1
    if _platform.system() == "Windows":
        from naturo.process import _get_console_session_id, _get_process_session_id
        _console_session = _get_console_session_id()
        _filter_session0 = _console_session >= 0

    # Build deduplicated list of windows to inspect
    targets = []
    seen_keys = set()

    for w in windows:
        if not w.is_visible or w.is_minimized:
            continue
        # Skip session 0 processes — they have no visible desktop UI (#350)
        if _filter_session0 and _get_process_session_id(w.pid) == 0:
            continue
        # Deduplicate by (PID, title) to keep distinct UWP windows (#252)
        key = (w.pid, w.title)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        targets.append(w)

    def _inspect_one(w):
        """Inspect a single window (thread-safe)."""
        return detect(
            pid=w.pid,
            exe=w.process_name,
            hwnd=w.handle,
            app_name=w.title or w.process_name,
            use_cache=False,  # Different windows may have different results
            quick=quick,
        )

    # (#395) Run inspections in parallel to avoid cumulative timeout
    # with many open windows.  Cap workers to avoid overwhelming the
    # OS with concurrent UIA/COM calls.
    from concurrent.futures import ThreadPoolExecutor, as_completed

    max_workers = min(len(targets), 4)
    results = []
    if max_workers > 0:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(_inspect_one, w): w for w in targets}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception:
                    pass  # skip windows that fail detection

    if json_output:
        click.echo(json_dumps({
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
