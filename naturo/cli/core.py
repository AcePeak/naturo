"""Core commands: capture, list, see, find, learn, tools.

Implements the Phase 1 "See" CLI commands for screen capture,
window listing, UI element tree inspection, and element search.
"""

import json as json_module
import platform

import click

from naturo.cli.error_helpers import json_error as _json_error_str
from naturo.errors import WindowNotFoundError
from naturo.cli.fuzzy_group import FuzzyGroup


def _get_backend():
    """Get the platform-appropriate backend.

    Returns:
        A Backend instance for the current platform.

    Raises:
        RuntimeError: If no backend is available (unsupported platform or
            missing dependencies like Peekaboo on macOS).
    """
    from naturo.backends.base import get_backend
    return get_backend()


def _platform_supports_gui() -> bool:
    """Check if the current platform has a GUI automation backend.

    Returns:
        True if Windows or macOS with Peekaboo installed.
    """
    system = platform.system()
    if system == "Windows":
        return True
    if system == "Darwin":
        import shutil
        return shutil.which("peekaboo") is not None
    return False


def _platform_error_msg(feature: str) -> str:
    """Build a user-friendly platform error message.

    Args:
        feature: Description of the feature (e.g. 'Screen capture').

    Returns:
        Error message string.
    """
    system = platform.system()
    if system == "Darwin":
        return (
            f"{feature} requires Peekaboo on macOS. "
            "Install it from https://github.com/AcePeak/peekaboo"
        )
    if system == "Linux":
        return f"{feature} is not yet supported on Linux (coming in Phase 7)."
    return f"{feature} is not supported on {system}."


# ── capture ─────────────────────────────────────


@click.group(cls=FuzzyGroup)
def capture():
    """Capture screenshots, video, or watch for changes."""
    pass


@capture.command()
@click.option("--app", help="Target application (name or partial match)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--screen", "-s", type=int, default=0, help="Screen/monitor index")
@click.option("--path", "-p", default=None, help="Output file path (default: capture.<format>)")
@click.option("--format", "fmt", type=click.Choice(["png", "jpg", "bmp"]), default="png", help="Image format (default: png)")
@click.option("--snapshot/--no-snapshot", "store_snapshot", default=True, help="Store result in snapshot (default: on)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def live(app, window_title, hwnd, screen, path, fmt, store_snapshot, json_output):
    """Capture a live screenshot.

    Captures the screen or a specific window and saves to a file.
    Use --hwnd to capture a specific window, or --screen to select a monitor.
    The screenshot is automatically stored in a snapshot (use --no-snapshot to skip).
    Output format is PNG by default (matching Peekaboo).
    """
    if not _platform_supports_gui():
        msg = _platform_error_msg("Screen capture")
        if json_output:
            click.echo(_json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(msg)
        raise SystemExit(1)

    # Resolve output path: use --path if given, else timestamped name
    if path is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        app_label = (app or "screen").lower().replace(" ", "-")
        path = f"naturo-{app_label}-{timestamp}.{fmt}"

    try:
        backend = _get_backend()
        if hwnd or app or window_title:
            # Resolve app/window_title to hwnd if needed
            target_hwnd = hwnd
            if not target_hwnd and hasattr(backend, '_resolve_hwnd'):
                target_hwnd = backend._resolve_hwnd(app=app, window_title=window_title)
            result = backend.capture_window(hwnd=target_hwnd or 0, output_path=path)
        else:
            # Validate screen index against available monitors
            if screen < 0:
                msg = f"--screen must be >= 0, got {screen}"
                if json_output:
                    click.echo(_json_error_str("INVALID_INPUT", msg))
                else:
                    click.echo(f"Error: {msg}", err=True)
                raise SystemExit(1)
            try:
                monitors = backend.list_monitors()
                if monitors and screen >= len(monitors):
                    msg = f"Screen index {screen} out of range (0-{len(monitors) - 1}). Use 'naturo list screens' to see available monitors."
                    if json_output:
                        click.echo(_json_error_str("INVALID_INPUT", msg))
                    else:
                        click.echo(f"Error: {msg}", err=True)
                    raise SystemExit(1)
            except NotImplementedError:
                pass  # Non-Windows: skip validation, let backend handle it
            result = backend.capture_screen(screen_index=screen, output_path=path)

        snapshot_id = None
        if store_snapshot:
            from naturo.snapshot import SnapshotManager
            mgr = SnapshotManager()
            snapshot_id = mgr.create_snapshot()
            metadata = {
                "window_handle": hwnd,
                "application_name": app,
                "window_title": window_title,
            }
            mgr.store_screenshot(snapshot_id, result.path, metadata)

        if json_output:
            out = {
                "success": True,
                "path": result.path,
                "width": result.width,
                "height": result.height,
                "format": result.format,
                "scale_factor": result.scale_factor,
                "dpi": result.dpi,
            }
            if snapshot_id:
                out["snapshot_id"] = snapshot_id
            click.echo(json_module.dumps(out))
        else:
            import os
            full_path = os.path.abspath(result.path)
            click.echo(f"Saved: {full_path} ({result.width}x{result.height})")
    except WindowNotFoundError as e:
        if json_output:
            click.echo(_json_error_str("WINDOW_NOT_FOUND", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        if json_output:
            click.echo(_json_error_str("CAPTURE_ERROR", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@capture.command(hidden=True)
@click.option("--app", help="Target application (name or partial match)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--screen", "-s", type=int, help="Screen/monitor index")
@click.option("--duration", "-d", type=float, default=5.0, help="Duration in seconds")
@click.option("--fps", type=int, default=30, help="Frames per second")
@click.option("--path", "-p", default="capture.mp4", help="Output file path")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def video(app, window_title, hwnd, screen, duration, fps, path, json_output):
    """Record video of screen or window."""
    msg = "Video recording is not implemented yet — coming in a future release."
    if json_output:
        click.echo(_json_error_str("NOT_IMPLEMENTED", msg))
    else:
        click.echo(f"Error: {msg}", err=True)
    raise SystemExit(1)


@capture.command(hidden=True)
@click.option("--app", help="Target application (name or partial match)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--interval", type=float, default=1.0, help="Check interval in seconds")
@click.option("--timeout", type=float, help="Max watch time in seconds")
@click.option("--path", "-p", help="Output directory")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def watch(app, window_title, hwnd, interval, timeout, path, json_output):
    """Watch for screen changes and capture on change."""
    msg = "Watch mode is not implemented yet — coming in a future release."
    if json_output:
        click.echo(_json_error_str("NOT_IMPLEMENTED", msg))
    else:
        click.echo(f"Error: {msg}", err=True)
    raise SystemExit(1)


# ── list ────────────────────────────────────────


@click.group("list", cls=FuzzyGroup)
def list_cmd():
    """List apps, windows, screens, or permissions."""
    pass


@list_cmd.command()
@click.option("--all", "show_all", is_flag=True, help="Show all processes (not just apps with windows)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def apps(ctx, show_all, json_output):
    """List running applications (delegates to 'app list')."""
    from naturo.cli.app_cmd import app_list
    ctx.invoke(app_list, show_all=show_all, json_output=json_output)


@list_cmd.command()
@click.option("--app", help="Target application (name or partial match)")
@click.option("--process-name", "app", default=None, hidden=True, help="")
@click.option("--pid", type=int, help="Process ID")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def windows(app, pid, json_output):
    """List open windows.

    Shows all visible top-level windows with their handles, titles,
    process names, and dimensions.
    """
    if not _platform_supports_gui():
        msg = _platform_error_msg("Window listing")
        if json_output:
            click.echo(_json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(msg)
        raise SystemExit(1)

    try:
        backend = _get_backend()
        win_list = backend.list_windows()

        # Apply filters
        if app:
            app_lower = app.lower()
            win_list = [w for w in win_list
                        if app_lower in w.title.lower()
                        or app_lower in w.process_name.lower()]
        if pid:
            win_list = [w for w in win_list if w.pid == pid]

        # Warn if empty result on Windows (may indicate no desktop session)
        if not win_list and platform.system() == "Windows":
            import os
            session_warning = ""
            session_id = os.environ.get("SESSIONNAME", "")
            if not session_id or session_id.lower() == "services":
                session_warning = " (Warning: no interactive desktop session detected — running via SSH or service?)"
            click.echo(
                f"Warning: no windows found{session_warning}",
                err=True,
            )

        if json_output:
            data = [
                {
                    "hwnd": w.handle,
                    "title": w.title,
                    "process_name": w.process_name,
                    "pid": w.pid,
                    "x": w.x,
                    "y": w.y,
                    "width": w.width,
                    "height": w.height,
                    "is_visible": w.is_visible,
                    "is_minimized": w.is_minimized,
                }
                for w in win_list
            ]
            click.echo(json_module.dumps({"success": True, "windows": data}, indent=2))
        else:
            if not win_list:
                click.echo("No windows found.")
                return
            # Table-like output
            click.echo(f"{'HWND':<16} {'PID':<8} {'SIZE':<14} {'TITLE'}")
            click.echo("-" * 70)
            for w in win_list:
                size = f"{w.width}x{w.height}"
                title = w.title[:40] if len(w.title) > 40 else w.title
                click.echo(f"{w.handle:<16} {w.pid:<8} {size:<14} {title}")
            click.echo(f"\n{len(win_list)} windows found.")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@list_cmd.command()
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def screens(json_output):
    """List connected screens/monitors.

    Shows monitor index, resolution, position, DPI scale factor, and
    whether the monitor is the primary display.
    """
    try:
        backend = _get_backend()
        monitors = backend.list_monitors()

        if json_output:
            items = []
            for m in monitors:
                item = {
                    "index": m.index,
                    "name": m.name,
                    "x": m.x,
                    "y": m.y,
                    "width": m.width,
                    "height": m.height,
                    "is_primary": m.is_primary,
                    "scale_factor": m.scale_factor,
                    "dpi": m.dpi,
                }
                if m.work_area:
                    item["work_area"] = m.work_area
                items.append(item)
            click.echo(json_module.dumps({"success": True, "monitors": items}, indent=2))
        else:
            if not monitors:
                click.echo("No monitors detected.")
                return
            click.echo(f"{'Index':<8} {'Resolution':<16} {'Position':<16} {'Scale':<8} {'DPI':<6} {'Primary'}")
            click.echo("-" * 72)
            for m in monitors:
                res = f"{m.width}x{m.height}"
                pos = f"({m.x}, {m.y})"
                primary = "✓" if m.is_primary else ""
                scale = f"{m.scale_factor}x"
                click.echo(f"{m.index:<8} {res:<16} {pos:<16} {scale:<8} {m.dpi:<6} {primary}")
            click.echo(f"\n{len(monitors)} monitor(s) found.")
    except NotImplementedError:
        msg = f"Monitor listing is not supported on {platform.system()} yet."
        if json_output:
            click.echo(_json_error_str("NOT_IMPLEMENTED", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)
    except Exception as e:
        if json_output:
            click.echo(_json_error_str("UNKNOWN_ERROR", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@list_cmd.command(hidden=True)
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def permissions(json_output):
    """List automation permissions status (UIAccess, admin, etc.)."""
    msg = "Permission listing is not implemented yet — coming in a future release."
    if json_output:
        click.echo(_json_error_str("NOT_IMPLEMENTED", msg))
    else:
        click.echo(f"Error: {msg}", err=True)
    raise SystemExit(1)


# ── see ─────────────────────────────────────────


@click.command()
@click.option("--app", help="Target application (name or partial match)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--pid", type=int, help="Process ID")
@click.option(
    "--mode",
    type=click.Choice(["full", "interactive", "fast"]),
    default="full",
    help="Analysis mode: full (all elements), interactive (clickable only), fast (quick scan)",
)
@click.option("--depth", "-d", type=int, default=3, help="Maximum tree depth (1-10)")
@click.option("--path", "-p", help="Save screenshot to path")
@click.option("--annotate", is_flag=True, help="Annotate screenshot with element labels")
@click.option("--snapshot/--no-snapshot", "store_snapshot", default=True, help="Store result in snapshot (default: on)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.option(
    "--backend", "--method", "-b", "-m",
    type=click.Choice(["uia", "msaa", "ia2", "jab", "auto"]),
    default="uia",
    help="Accessibility backend / interaction method: uia (default), msaa (legacy apps), ia2 (Firefox/Thunderbird), jab (Java/Swing), auto",
)
def see(app, window_title, hwnd, pid, mode, depth, path, annotate, store_snapshot, json_output, backend):
    """Capture screenshot and analyze UI elements.

    Inspects the UI element tree of the foreground window (or a specific
    window identified by --hwnd). Shows the element hierarchy with roles,
    names, and bounding rectangles.  Results are stored in a snapshot so
    subsequent commands can reference elements by ID.

    Use --backend msaa for legacy applications (MFC, VB6, Delphi) that
    don't expose UIAutomation elements. Use --backend ia2 for IA2-enabled
    applications (Firefox, Thunderbird, LibreOffice). Use --backend auto to
    try UIA first, then IA2, then MSAA automatically.
    """
    # BUG-028: Validate --depth range (before platform check — input validation first)
    if depth < 1 or depth > 10:
        msg = f"--depth must be between 1 and 10, got {depth}"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    if not _platform_supports_gui():
        msg = _platform_error_msg("UI inspection")
        if json_output:
            click.echo(_json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(msg)
        raise SystemExit(1)

    try:
        be = _get_backend()
        tree = be.get_element_tree(
            app=app, window_title=window_title, hwnd=hwnd, depth=depth,
            backend=backend,
        )

        if tree is None:
            msg = "No window found or UI tree is empty."
            if json_output:
                click.echo(_json_error_str("WINDOW_NOT_FOUND", msg))
            else:
                click.echo(msg)
            raise SystemExit(1)

        snapshot_id = None
        if store_snapshot:
            from naturo.snapshot import SnapshotManager
            from naturo.models.snapshot import UIElement

            mgr = SnapshotManager()
            snapshot_id = mgr.create_snapshot()

            # Flatten element tree into ui_map and build ref→element mapping
            # (BUG-071: sequential refs e1, e2, ... for click integration)
            ui_map = {}
            _ref_seq = [0]
            ref_map = {}  # "e1" → element_id (backend id)

            def _flatten(el, parent_id=None):
                _ref_seq[0] += 1
                ref = f"e{_ref_seq[0]}"
                child_ids = [c.id for c in el.children]
                props = getattr(el, "properties", {})
                ui_map[el.id] = UIElement(
                    id=el.id,
                    element_id=f"element_{el.id}",
                    role=el.role,
                    title=el.name,
                    label=el.name,
                    value=el.value,
                    frame=(el.x, el.y, el.width, el.height),
                    is_actionable=getattr(el, "is_actionable", False),
                    parent_id=props.get("parent_id", parent_id),
                    children=child_ids,
                    keyboard_shortcut=props.get("keyboard_shortcut"),
                )
                ref_map[ref] = el.id
                for child in el.children:
                    _flatten(child, parent_id=el.id)

            _flatten(tree)
            mgr.store_detection_result(snapshot_id, ui_map)
            # Persist ref mapping so click/type can resolve e<N> refs
            mgr.store_ref_map(snapshot_id, ref_map)

            # Optionally capture screenshot into snapshot
            if path:
                result = backend.capture_screen(output_path=path)
                metadata = {
                    "window_handle": hwnd,
                    "application_name": app,
                    "window_title": window_title,
                }
                mgr.store_screenshot(snapshot_id, result.path, metadata)

        if json_output:
            def to_dict(el):
                """Convert ElementInfo tree to a JSON-serializable dict."""
                d = {
                    "id": el.id,
                    "role": el.role,
                    "name": el.name,
                    "value": el.value,
                    "x": el.x,
                    "y": el.y,
                    "width": el.width,
                    "height": el.height,
                    "children": [to_dict(c) for c in el.children],
                }
                # Include hierarchy/shortcut info from properties
                props = getattr(el, "properties", {})
                if props.get("parent_id"):
                    d["parent_id"] = props["parent_id"]
                if props.get("keyboard_shortcut"):
                    d["keyboard_shortcut"] = props["keyboard_shortcut"]
                return d
            out = to_dict(tree)
            if snapshot_id:
                out["snapshot_id"] = snapshot_id

            # Add DPI context so AI agents know coordinate scaling
            try:
                dpi_scale = be.get_dpi_scale(0) if hasattr(be, "get_dpi_scale") else 1.0
                monitors = be.list_monitors()
                primary = monitors[0] if monitors else None
                out["dpi_context"] = {
                    "scale_factor": primary.scale_factor if primary else dpi_scale,
                    "dpi": primary.dpi if primary else 96,
                    "note": "Element coordinates are in physical (pixel) space.",
                }
            except Exception:
                out["dpi_context"] = {"scale_factor": 1.0, "dpi": 96, "note": "Element coordinates are in physical (pixel) space."}

            click.echo(json_module.dumps(out, indent=2))
        else:
            # BUG-071: include short element IDs (e1, e2, ...) that can be
            # passed to ``naturo click e3`` for quick interaction.
            _ref_counter = [0]

            def print_tree(el, indent=0):
                """Print element tree with short element refs."""
                _ref_counter[0] += 1
                ref = f"e{_ref_counter[0]}"
                prefix = "  " * indent
                name_str = f' "{el.name}"' if el.name else ""
                pos_str = f" ({el.x},{el.y} {el.width}x{el.height})"
                click.echo(f"{prefix}[{el.role}]{name_str}{pos_str} {ref}")
                for child in el.children:
                    print_tree(child, indent + 1)

            print_tree(tree)
            if snapshot_id:
                click.echo(f"\nSnapshot: {snapshot_id}")
                click.echo("Tip: use 'naturo click e<N>' to click an element by its ref.")

        # Generate annotated screenshot
        if annotate and store_snapshot and snapshot_id:
            try:
                from naturo.annotate import annotate_screenshot
                snap = mgr.get_snapshot(snapshot_id)
                if snap.screenshot_path:
                    elements = list(snap.ui_map.values())
                    annotated_path = annotate_screenshot(
                        snap.screenshot_path,
                        elements,
                    )
                    mgr.store_annotated(snapshot_id, annotated_path)
                    if not json_output:
                        click.echo(f"Annotated: {annotated_path}")
                else:
                    if not json_output:
                        click.echo("Warning: --annotate requires a screenshot (use --path)")
            except ImportError:
                click.echo("Warning: Pillow required for --annotate. Install: pip install naturo[annotate]", err=True)

        # Capture screenshot (when not already done above)
        if path and not store_snapshot:
            result = backend.capture_screen(output_path=path)
            click.echo(f"\nScreenshot saved: {result.path}")

    except WindowNotFoundError as e:
        if json_output:
            click.echo(_json_error_str("WINDOW_NOT_FOUND", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
    except Exception as e:
        if json_output:
            click.echo(_json_error_str("UNKNOWN_ERROR", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# ── find ────────────────────────────────────────


@click.command("find")
@click.argument("query", required=False, default=None)
@click.option("--query", "-q", "query_opt", default=None,
              help="Search query (alternative to positional arg; survives shell glob expansion)")
@click.option("--all", "find_all", is_flag=True,
              help="Find all elements (equivalent to query \"*\"). Safe from shell glob expansion.")
@click.option("--role", help="Filter by element role (e.g., Button, Edit)")
@click.option("--actionable", is_flag=True, help="Only show actionable elements")
@click.option("--depth", "-d", type=int, default=5, help="Maximum tree depth (1-10)")
@click.option("--limit", type=int, default=50, help="Maximum number of results")
@click.option("--ai", is_flag=True, help="Use AI vision to find element by natural language")
@click.option("--provider", type=click.Choice(["auto", "anthropic", "openai", "ollama"]),
              default="auto", help="AI provider (for --ai mode)")
@click.option("--screenshot", type=click.Path(), default=None,
              help="Use existing screenshot (for --ai mode)")
@click.option("--app", default=None, help="Target app window")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.option(
    "--backend", "--method", "-b", "-m",
    type=click.Choice(["uia", "msaa", "ia2", "jab", "auto"]),
    default="uia",
    help="Accessibility backend / interaction method: uia (default), msaa (legacy apps), ia2 (Firefox/Thunderbird), jab (Java/Swing), auto",
)
def find_cmd(query, query_opt, find_all, role, actionable, depth, limit, ai, provider, screenshot, app, json_output, backend):
    """Search for UI elements matching a query.

    Supports fuzzy name matching, role filtering, and combined queries.
    Use --ai for natural language element finding powered by AI vision.
    Use --backend msaa for legacy applications that lack UIA support.
    Use --backend ia2 for IA2-enabled apps (Firefox, Thunderbird, LibreOffice).

    \b
    Examples:
        naturo find "Save"                      # fuzzy name search
        naturo find "Button:Save"               # role + name
        naturo find "role:Edit"                  # by role only
        naturo find --all --actionable           # all actionable elements (SSH-safe)
        naturo find --all --role Button          # all buttons
        naturo find "the save button" --ai       # AI vision search
        naturo find "Save" --app "Notepad"              # search in specific app
        naturo find "search field" --ai --app "Chrome"  # AI + specific app
        naturo find "OK" --backend msaa          # MSAA for legacy apps
    """
    # Resolve query: --all flag → wildcard, --query option → override positional
    if find_all:
        query = "*"
    elif query_opt is not None:
        query = query_opt
    # else: query is the positional arg (may be None)

    if query is None:
        # When --actionable or --role is set, treat missing query as wildcard
        if actionable or role:
            query = "*"
        else:
            msg = "Missing argument 'QUERY'. Provide as positional arg or --query/-q option."
            if json_output:
                click.echo(_json_error_str("INVALID_INPUT", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)

    # AI vision mode — natural language element finding
    if ai:
        _find_with_ai(query, provider, screenshot, app, json_output)
        return

    # BUG-028: Validate --depth range (before platform check — input validation first)
    if depth < 1 or depth > 10:
        msg = f"--depth must be between 1 and 10, got {depth}"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    if not _platform_supports_gui():
        msg = _platform_error_msg("UI inspection")
        if json_output:
            click.echo(_json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(msg)
        raise SystemExit(1)

    try:
        be = _get_backend()
        tree = be.get_element_tree(app=app, depth=depth, backend=backend)
        if tree is None:
            msg = "No window found or UI tree is empty."
            if json_output:
                click.echo(_json_error_str("WINDOW_NOT_FOUND", msg))
            else:
                click.echo(msg)
            raise SystemExit(1)

        from naturo.search import search_elements
        # Convert backend ElementInfo tree to bridge ElementInfo for search
        from naturo.bridge import ElementInfo as BridgeElementInfo

        def to_bridge(el):
            """Convert backend ElementInfo to bridge ElementInfo."""
            return BridgeElementInfo(
                id=el.id,
                role=el.role,
                name=el.name,
                value=el.value,
                x=el.x,
                y=el.y,
                width=el.width,
                height=el.height,
                children=[to_bridge(c) for c in el.children],
                parent_id=el.properties.get("parent_id"),
                keyboard_shortcut=el.properties.get("keyboard_shortcut"),
            )

        bridge_tree = to_bridge(tree)
        results = search_elements(
            bridge_tree,
            query,
            role_filter=role,
            actionable_only=actionable,
            max_results=limit,
        )

        if json_output:
            data = [
                {
                    "id": r.element.id,
                    "role": r.element.role,
                    "name": r.element.name,
                    "value": r.element.value,
                    "x": r.element.x,
                    "y": r.element.y,
                    "width": r.element.width,
                    "height": r.element.height,
                    "breadcrumb": r.breadcrumb_str,
                    "keyboard_shortcut": r.element.keyboard_shortcut,
                }
                for r in results
            ]
            click.echo(json_module.dumps({"success": True, "elements": data, "count": len(data)}, indent=2))
        else:
            if not results:
                click.echo(f"No elements found matching: {query}")
                return

            for i, r in enumerate(results):
                el = r.element
                name_str = f' "{el.name}"' if el.name else ""
                pos_str = f"({el.x},{el.y} {el.width}x{el.height})"
                shortcut = f" [{el.keyboard_shortcut}]" if el.keyboard_shortcut else ""
                click.echo(f"  {i}. [{el.role}]{name_str} {pos_str}{shortcut}")
                click.echo(f"     {r.breadcrumb_str}")

            click.echo(f"\n{len(results)} element(s) found.")

    except Exception as e:
        if json_output:
            click.echo(_json_error_str("UNKNOWN_ERROR", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


def _find_with_ai(query, provider_name, screenshot, app, json_output):
    """AI-powered element finding via naturo find --ai.

    Args:
        query: Natural language description of the element.
        provider_name: AI provider name.
        screenshot: Optional screenshot path.
        app: Optional target application window.
        json_output: Whether to output JSON.
    """
    try:
        from naturo.ai_find import ai_find_element
    except ImportError as e:
        msg = f"AI find dependencies not available: {e}"
        if json_output:
            click.echo(_json_error_str("MISSING_DEPENDENCY", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    # Validate screenshot path
    if screenshot and not __import__("os").path.exists(screenshot):
        msg = f"Screenshot file not found: {screenshot}"
        if json_output:
            click.echo(_json_error_str("FILE_NOT_FOUND", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    try:
        result = ai_find_element(
            query,
            provider_name=provider_name,
            window_title=app,
            screenshot_path=screenshot,
        )
    except Exception as e:
        msg = str(e)
        code = "AI_FIND_FAILED"
        if "unavailable" in msg.lower() or "api key" in msg.lower():
            code = "AI_PROVIDER_UNAVAILABLE"
        elif "capture" in msg.lower():
            code = "CAPTURE_FAILED"
        if json_output:
            click.echo(json_module.dumps({"success": False, "error": {"code": code, "message": msg}}))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    if json_output:
        output = {
            "success": result.found,
            "description": result.description,
            "confidence": result.confidence,
            "method": result.method,
            "model": result.model,
            "tokens_used": result.tokens_used,
        }
        if result.ai_bounds:
            output["ai_bounds"] = result.ai_bounds
        if result.element:
            output["element"] = result.element
        if not result.found:
            output["error"] = {
                "code": "ELEMENT_NOT_FOUND",
                "message": f"AI could not locate: {query}",
            }
        click.echo(json_module.dumps(output, indent=2))
    else:
        if not result.found:
            click.echo(f"Element not found: {query}")
            if result.description:
                click.echo(f"  AI says: {result.description}")
            raise SystemExit(1)

        click.echo(f"Found: {result.description}")
        click.echo(f"  Confidence: {result.confidence:.0%}")
        click.echo(f"  Method: {result.method}")
        if result.ai_bounds:
            b = result.ai_bounds
            click.echo(f"  AI bounds: ({b.get('x', '?')}, {b.get('y', '?')}) "
                        f"{b.get('width', '?')}x{b.get('height', '?')}")
        if result.element:
            el = result.element
            click.echo(f"  UIA match: [{el.get('role', '')}] \"{el.get('name', '')}\"")
            eb = el.get("bounds", {})
            click.echo(f"  UIA bounds: ({eb.get('x', '?')}, {eb.get('y', '?')}) "
                        f"{eb.get('width', '?')}x{eb.get('height', '?')}")
            click.echo(f"  Match distance: {el.get('match_distance', '?')} px")
        click.echo(f"  [{result.model}, {result.tokens_used} tokens]", err=True)

    if not result.found:
        raise SystemExit(1)


# ── menu (standalone) ───────────────────────────


@click.command("menu_cmd")
@click.option("--app", help="Application name")
@click.option("--flat", is_flag=True, help="Flatten menu tree into paths")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def menu_inspect(app, flat, json_output):
    """List the menu bar structure of the foreground application.

    Traverses the application's MenuBar via UIAutomation and displays
    all menu items with their keyboard shortcuts.
    """
    if not _platform_supports_gui():
        msg = _platform_error_msg("Menu inspection")
        if json_output:
            click.echo(_json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(msg)
        raise SystemExit(1)

    try:
        backend = _get_backend()

        # BUG-026: Check if app exists before inspecting menus
        if app:
            try:
                from naturo.process import find_process
                app_info = find_process(app)
                if not app_info:
                    msg = f"Application not found: {app}"
                    if json_output:
                        click.echo(_json_error_str("APP_NOT_FOUND", msg))
                    else:
                        click.echo(f"Error: {msg}", err=True)
                    raise SystemExit(1)
            except ImportError:
                pass  # find_process not available, fall through to get_menu_items
            except SystemExit:
                raise
            except Exception:
                pass  # find_process failed for other reasons, fall through

        items = backend.get_menu_items(window_title=app)

        if not items:
            msg = "No menu items found."
            if json_output:
                click.echo(_json_error_str("NO_MENU_ITEMS", msg))
            else:
                click.echo(msg)
            raise SystemExit(1)

        if json_output:
            if flat:
                flat_items = []
                for item in items:
                    flat_items.extend(item.flatten())
                click.echo(json_module.dumps({"success": True, "menu_items": flat_items}, indent=2))
            else:
                click.echo(json_module.dumps({"success": True, "menu_items": [item.to_dict() for item in items]}, indent=2))
        else:
            if flat:
                for item in items:
                    for entry in item.flatten():
                        shortcut = f"  [{entry['shortcut']}]" if entry.get("shortcut") else ""
                        click.echo(f"  {entry['path']}{shortcut}")
            else:
                def print_menu(item, indent=0):
                    """Recursively print a menu item and its submenus with indentation."""
                    prefix = "  " * indent
                    shortcut = f" [{item.shortcut}]" if item.shortcut else ""
                    state = ""
                    if not item.enabled:
                        state += " (disabled)"
                    if item.checked:
                        state += " (✓)"
                    click.echo(f"{prefix}{item.name}{shortcut}{state}")
                    if item.submenu:
                        for sub in item.submenu:
                            print_menu(sub, indent + 1)

                for item in items:
                    print_menu(item)

    except NotImplementedError:
        msg = "Menu inspection not supported on this platform."
        if json_output:
            click.echo(_json_error_str("NOT_SUPPORTED", msg))
        else:
            click.echo(msg)
        raise SystemExit(1)
    except Exception as e:
        if json_output:
            click.echo(_json_error_str("UNKNOWN_ERROR", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


# ── learn ───────────────────────────────────────


@click.command()
@click.argument("topic", required=False)
def learn(topic):
    """Show usage guide and tutorials.

    Without TOPIC, shows an overview. With TOPIC, shows detailed help
    including common commands, examples, and tips.
    """
    topics = {
        "capture": {
            "summary": "Capture screenshots, video, or watch for changes.",
            "guide": """\
  Screenshots
  -----------
    naturo capture live --path screenshot.png   Save a screenshot
    naturo capture live --json                  Screenshot with metadata (JSON)
    naturo capture live --app "Notepad"         Capture a specific app window

  Snapshots (element-annotated screenshots)
  -----------------------------------------
    naturo capture live --path snap.png          Capture + store snapshot
    naturo snapshot list                         List saved snapshots
    naturo snapshot clean                        Remove old snapshots

  Recording
  ---------
    naturo record start                         Start screen recording
    naturo record stop                          Stop and save recording
    naturo record list                          List recordings

  Watch for Changes
  -----------------
    naturo diff --snapshot ID1 --snapshot ID2    Compare two snapshots
    naturo diff --window "Notepad"              Capture before/after diff

  Tips
  ----
    • Add --json to any command for structured output
    • Use --app or --window-title to capture a specific window
    • Snapshots annotate UI elements for AI-assisted automation""",
        },
        "interaction": {
            "summary": "Click, type, press, hotkey, scroll, drag, move, paste.",
            "guide": """\
  Mouse
  -----
    naturo click --coords 500 300               Click at coordinates (x, y)
    naturo click --coords 500 300 --right        Right-click
    naturo click --coords 500 300 --double       Double-click
    naturo click "Submit"                        Click element by text
    naturo drag --from-coords 100 200 --to-coords 400 500
                                                Drag from (100,200) to (400,500)
    naturo move --coords 500 300                Move mouse cursor
    naturo scroll down                          Scroll down
    naturo scroll up --amount 5                 Scroll up 5 clicks

  Keyboard
  --------
    naturo type "Hello, World!"                 Type text
    naturo press enter                          Press a single key
    naturo hotkey ctrl+s                        Key combination (Ctrl+S)
    naturo hotkey alt+f4                        Close active window
    naturo hotkey ctrl+shift+esc                Open Task Manager

  AI-Powered Interaction
  ----------------------
    naturo find "Submit button"                 Find element by description
    naturo see                                  Describe what's on screen

  Tips
  ----
    • Use naturo find to locate elements without knowing coordinates
    • Combine with naturo capture to verify actions visually
    • All commands support --json for automation pipelines""",
        },
        "system": {
            "summary": "App, window, menu, clipboard, dialog, open.",
            "guide": """\
  Applications
  ------------
    naturo app list                             List running applications
    naturo app launch notepad                   Launch an application
    naturo app quit notepad                     Close an application
    naturo app switch "Google Chrome"            Switch to an app
    naturo app find "Visual Studio"             Find apps by name

  Windows
  -------
    naturo list windows                         List all windows
    naturo window focus --title "Untitled"       Focus a window by title
    naturo window minimize --title "Notepad"     Minimize a window
    naturo window maximize --title "Notepad"     Maximize a window
    naturo window close --title "Notepad"        Close a window
    naturo window move --title "Notepad" --x 100 --y 100
    naturo window resize --title "Notepad" --width 800 --height 600

  Clipboard
  ---------
    naturo clipboard get                        Read clipboard content
    naturo clipboard set "copied text"          Write to clipboard

  Dialogs
  -------
    naturo dialog detect                        Detect open dialogs
    naturo dialog accept                        Accept/OK a dialog
    naturo dialog dismiss                       Cancel/dismiss a dialog

  Opening Files & URLs
  --------------------
    naturo open https://example.com             Open URL in browser
    naturo open document.pdf                    Open file with default app

  Tips
  ----
    • naturo list screens shows monitor info
    • Use --json on any command for structured output
    • App names are case-insensitive for most commands""",
        },
        "windows": {
            "summary": "Windows-specific: taskbar, tray, desktop, registry, service.",
            "guide": """\
  Taskbar & System Tray
  ---------------------
    naturo taskbar list                         List taskbar items
    naturo taskbar click "Chrome"               Click a taskbar icon
    naturo tray list                            List system tray icons
    naturo tray click "Volume"                  Click a tray icon

  Registry
  --------
    naturo registry list HKCU\\Software          List registry subkeys
    naturo registry get HKCU\\Software\\MyApp -v Setting
    naturo registry set HKCU\\Software\\MyApp -v Key -d "value"
    naturo registry search HKCU\\Software "keyword"

  Services
  --------
    naturo service list                         List all services
    naturo service list --state running         Only running services
    naturo service status Spooler               Get service details
    naturo service start Spooler                Start a service
    naturo service stop Spooler                 Stop a service
    naturo service restart Spooler              Restart a service

  Virtual Desktops
  ----------------
    naturo desktop list                         List virtual desktops
    naturo desktop switch 2                     Switch to desktop 2
    (Requires pyvda: pip install pyvda)

  Tips
  ----
    • Registry operations support HKCU, HKLM, HKCR, HKU, HKCC
    • Service commands require appropriate permissions
    • Use --json for automation-friendly output""",
        },
        "extensions": {
            "summary": "Enterprise: excel, java, sap automation.",
            "guide": """\
  Excel (COM Automation)
  ----------------------
    naturo excel open report.xlsx               Open a workbook
    naturo excel read report.xlsx A1             Read a cell
    naturo excel read report.xlsx "A1:D10"       Read a range
    naturo excel write report.xlsx B2 "Hello"    Write to a cell
    naturo excel list-sheets report.xlsx         List sheets
    naturo excel run-macro data.xlsm "MyMacro"   Run a VBA macro
    naturo excel info report.xlsx                Used range info
    (Requires Microsoft Excel and pywin32)

  Electron/CEF Apps
  -----------------
    naturo electron detect slack                Detect if app is Electron
    naturo electron list                        List all Electron apps
    naturo electron connect slack               Connect via CDP
    naturo electron launch "C:\\App.exe" --port 9229
    (Enables DOM automation via Chrome DevTools Protocol)

  Chrome DevTools
  ---------------
    naturo chrome tabs                          List Chrome tabs
    naturo chrome tabs --port 9229              Connect to custom port

  Java Access Bridge (planned)
  ----------------------------
    Java UI automation via JAB is on the roadmap.
    Will enable inspection and control of Swing/AWT applications.

  SAP GUI Scripting (planned)
  ---------------------------
    SAP GUI automation via scripting API is on the roadmap.
    Will enable transaction execution and form interaction.

  Tips
  ----
    • Electron automation unlocks DOM access for desktop apps
    • Excel operations preserve formatting and formulas
    • Use --json for all commands for pipeline integration""",
        },
        "ai": {
            "summary": "AI agent and MCP server integration.",
            "guide": """\
  MCP Server (Model Context Protocol)
  ------------------------------------
    naturo mcp start                            Start MCP server (stdio)
    naturo mcp tools                            List all MCP tools
    naturo mcp tools --json                     Tool list as JSON

  AI Agent
  --------
    naturo agent "Open Notepad and type hello"
    naturo agent --model gpt-4o "Fill in the form"
    (Provides autonomous UI automation via AI vision)

  AI-Powered Commands
  -------------------
    naturo see                                  Describe current screen
    naturo find "Login button"                  Find UI element by description
    naturo describe                             Detailed screen analysis

  Integration with LLM Frameworks
  --------------------------------
    Use naturo as an MCP server in Claude Desktop, Cursor, or any
    MCP-compatible client:

    {
      "mcpServers": {
        "naturo": {
          "command": "naturo",
          "args": ["mcp", "start"]
        }
      }
    }

  Tips
  ----
    • MCP server exposes all naturo capabilities as tools
    • 82 tools covering capture, interaction, system, and more
    • Use --json output format for reliable LLM parsing
    • AI find works best with descriptive element names""",
        },
    }
    topic_names = list(topics.keys())
    if topic and topic in topics:
        info = topics[topic]
        click.echo(f"\n  {topic}: {info['summary']}\n")
        click.echo(info["guide"])
        click.echo()
    elif topic and topic not in topics:
        click.echo(f"Error: Unknown topic: {topic}", err=True)
        click.echo(f"Available topics: {', '.join(topic_names)}", err=True)
        raise SystemExit(1)
    else:
        click.echo("\nNaturo — Windows desktop automation engine\n")
        click.echo("Available topics:")
        for name in topic_names:
            click.echo(f"  {name:15s} {topics[name]['summary']}")
        click.echo("\nRun: naturo learn <topic> for details.")


# ── tools ───────────────────────────────────────


@click.command(hidden=True)
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def tools(json_output):
    """List available automation tools and backends.

    Shows which native backends are available (UIA, MSAA, Java Bridge, etc.).
    """
    msg = "Tools listing is not implemented yet — coming in a future release."
    if json_output:
        click.echo(_json_error_str("NOT_IMPLEMENTED", msg))
    else:
        click.echo(f"Error: {msg}", err=True)
    raise SystemExit(1)
