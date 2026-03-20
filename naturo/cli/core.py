"""Core commands: capture, list, see, find, learn, tools.

Implements the Phase 1 "See" CLI commands for screen capture,
window listing, UI element tree inspection, and element search.
"""

import json as json_module
import platform

import click

from naturo.cli.error_helpers import json_error as _json_error_str
from naturo.errors import WindowNotFoundError


def _get_backend():
    """Get the platform-appropriate backend.

    Returns:
        A Backend instance for the current platform.
    """
    from naturo.backends.base import get_backend
    return get_backend()


# ── capture ─────────────────────────────────────


@click.group()
def capture():
    """Capture screenshots, video, or watch for changes."""
    pass


@capture.command()
@click.option("--app", help="Application name to capture")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle (HWND)")
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
    if platform.system() != "Windows":
        msg = "Screen capture requires Windows (naturo_core.dll)."
        if json_output:
            click.echo(_json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(msg)
        raise SystemExit(1)

    # Resolve output path: use --path if given, else capture.<format>
    if path is None:
        path = f"capture.{fmt}"

    try:
        backend = _get_backend()
        if hwnd or app or window_title:
            # Resolve app/window_title to hwnd if needed
            target_hwnd = hwnd
            if not target_hwnd and hasattr(backend, '_resolve_hwnd'):
                target_hwnd = backend._resolve_hwnd(app=app, window_title=window_title)
            result = backend.capture_window(hwnd=target_hwnd or 0, output_path=path)
        else:
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
@click.option("--app", help="Application name")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle (HWND)")
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
@click.option("--app", help="Application name")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle (HWND)")
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


@click.group("list")
def list_cmd():
    """List apps, windows, screens, or permissions."""
    pass


@list_cmd.command(hidden=True)
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def apps(json_output):
    """List running applications."""
    msg = "Application listing is not implemented yet — coming in a future release."
    if json_output:
        click.echo(_json_error_str("NOT_IMPLEMENTED", msg))
    else:
        click.echo(f"Error: {msg}", err=True)
    raise SystemExit(1)


@list_cmd.command()
@click.option("--app", help="Filter by application name")
@click.option("--process-name", help="Filter by process name")
@click.option("--pid", type=int, help="Filter by process ID")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def windows(app, process_name, pid, json_output):
    """List open windows.

    Shows all visible top-level windows with their handles, titles,
    process names, and dimensions.
    """
    if platform.system() != "Windows":
        msg = "Window listing requires Windows (naturo_core.dll)."
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
            win_list = [w for w in win_list if app_lower in w.title.lower()]
        if process_name:
            pn_lower = process_name.lower()
            win_list = [w for w in win_list if pn_lower in w.process_name.lower()]
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


@list_cmd.command(hidden=True)
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def screens(json_output):
    """List connected screens/monitors."""
    msg = "Screen listing is not implemented yet — coming in a future release."
    if json_output:
        click.echo(_json_error_str("NOT_IMPLEMENTED", msg))
    else:
        click.echo(f"Error: {msg}", err=True)
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
@click.option("--app", help="Application name")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle (HWND)")
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
def see(app, window_title, hwnd, pid, mode, depth, path, annotate, store_snapshot, json_output):
    """Capture screenshot and analyze UI elements.

    Inspects the UI element tree of the foreground window (or a specific
    window identified by --hwnd). Shows the element hierarchy with roles,
    names, and bounding rectangles.  Results are stored in a snapshot so
    subsequent commands can reference elements by ID.
    """
    # BUG-028: Validate --depth range (before platform check — input validation first)
    if depth < 1 or depth > 10:
        msg = f"--depth must be between 1 and 10, got {depth}"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    if platform.system() != "Windows":
        msg = "UI inspection requires Windows (naturo_core.dll)."
        if json_output:
            click.echo(_json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(msg)
        raise SystemExit(1)

    try:
        backend = _get_backend()
        tree = backend.get_element_tree(
            app=app, window_title=window_title, hwnd=hwnd, depth=depth,
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

            # Flatten element tree into ui_map
            ui_map = {}

            def _flatten(el, parent_id=None):
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
                for child in el.children:
                    _flatten(child, parent_id=el.id)

            _flatten(tree)
            mgr.store_detection_result(snapshot_id, ui_map)

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
            click.echo(json_module.dumps(out, indent=2))
        else:
            def print_tree(el, indent=0):
                """Print element tree in a readable indented format."""
                prefix = "  " * indent
                name_str = f' "{el.name}"' if el.name else ""
                pos_str = f" ({el.x},{el.y} {el.width}x{el.height})"
                click.echo(f"{prefix}[{el.role}]{name_str}{pos_str}")
                for child in el.children:
                    print_tree(child, indent + 1)

            print_tree(tree)
            if snapshot_id:
                click.echo(f"\nSnapshot: {snapshot_id}")

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
@click.argument("query")
@click.option("--role", help="Filter by element role (e.g., Button, Edit)")
@click.option("--actionable", is_flag=True, help="Only show actionable elements")
@click.option("--depth", "-d", type=int, default=5, help="Maximum tree depth (1-10)")
@click.option("--limit", type=int, default=50, help="Maximum number of results")
@click.option("--ai", is_flag=True, help="Use AI vision to find element by natural language")
@click.option("--provider", type=click.Choice(["auto", "anthropic", "openai", "ollama"]),
              default="auto", help="AI provider (for --ai mode)")
@click.option("--screenshot", type=click.Path(), default=None,
              help="Use existing screenshot (for --ai mode)")
@click.option("--app", "ai_app", default=None, help="Target app window (for --ai mode)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def find_cmd(query, role, actionable, depth, limit, ai, provider, screenshot, ai_app, json_output):
    """Search for UI elements matching a query.

    Supports fuzzy name matching, role filtering, and combined queries.
    Use --ai for natural language element finding powered by AI vision.

    \b
    Examples:
        naturo find "Save"                      # fuzzy name search
        naturo find "Button:Save"               # role + name
        naturo find "role:Edit"                  # by role only
        naturo find "*" --actionable             # all actionable elements
        naturo find "the save button" --ai       # AI vision search
        naturo find "search field" --ai --app "Chrome"  # AI + specific app
    """
    # AI vision mode — natural language element finding
    if ai:
        _find_with_ai(query, provider, screenshot, ai_app, json_output)
        return

    # BUG-028: Validate --depth range (before platform check — input validation first)
    if depth < 1 or depth > 10:
        msg = f"--depth must be between 1 and 10, got {depth}"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    if platform.system() != "Windows":
        msg = "UI inspection requires Windows (naturo_core.dll)."
        if json_output:
            click.echo(_json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(msg)
        raise SystemExit(1)

    try:
        backend = _get_backend()
        tree = backend.get_element_tree(depth=depth)
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
            click.echo(json_module.dumps(data, indent=2))
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
    if platform.system() != "Windows":
        msg = "Menu inspection requires Windows (naturo_core.dll)."
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
                click.echo(json_module.dumps(flat_items, indent=2))
            else:
                click.echo(json_module.dumps([item.to_dict() for item in items], indent=2))
        else:
            if flat:
                for item in items:
                    for entry in item.flatten():
                        shortcut = f"  [{entry['shortcut']}]" if entry.get("shortcut") else ""
                        click.echo(f"  {entry['path']}{shortcut}")
            else:
                def print_menu(item, indent=0):
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

    Without TOPIC, shows an overview. With TOPIC, shows detailed help.
    """
    topics = {
        "capture": "Capture screenshots, video, or watch for changes.",
        "interaction": "Click, type, press, hotkey, scroll, drag, move, paste.",
        "system": "App, window, menu, clipboard, dialog, open.",
        "windows": "Windows-specific: taskbar, tray, desktop, registry, service.",
        "extensions": "Enterprise: excel, java, sap automation.",
        "ai": "AI agent and MCP server integration.",
    }
    if topic and topic in topics:
        click.echo(f"\n  {topic}: {topics[topic]}\n")
    elif topic and topic not in topics:
        click.echo(f"Error: Unknown topic: {topic}", err=True)
        click.echo(f"Available topics: {', '.join(topics.keys())}", err=True)
        raise SystemExit(1)
    else:
        click.echo("\nNaturo — Windows desktop automation engine\n")
        click.echo("Available topics:")
        for t, desc in topics.items():
            click.echo(f"  {t:15s} {desc}")
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
