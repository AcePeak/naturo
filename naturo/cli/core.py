"""Core commands: capture, list, see, learn, tools.

Implements the Phase 1 "See" CLI commands for screen capture,
window listing, and UI element tree inspection.
"""

import json as json_module
import platform

import click


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
@click.option("--path", "-p", default="capture.bmp", help="Output file path")
@click.option("--format", "fmt", type=click.Choice(["png", "jpg", "bmp"]), default="bmp", help="Image format")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def live(app, window_title, hwnd, screen, path, fmt, json_output):
    """Capture a live screenshot.

    Captures the screen or a specific window and saves to a file.
    Use --hwnd to capture a specific window, or --screen to select a monitor.
    """
    if platform.system() != "Windows":
        click.echo("Screen capture requires Windows (naturo_core.dll).")
        return

    try:
        backend = _get_backend()
        if hwnd:
            result = backend.capture_window(hwnd=hwnd, output_path=path)
        else:
            result = backend.capture_screen(screen_index=screen, output_path=path)

        if json_output:
            click.echo(json_module.dumps({
                "path": result.path,
                "width": result.width,
                "height": result.height,
                "format": result.format,
            }))
        else:
            click.echo(f"Saved: {result.path} ({result.width}x{result.height})")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)


@capture.command()
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
    click.echo("Not implemented yet — coming in Phase 3")


@capture.command()
@click.option("--app", help="Application name")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle (HWND)")
@click.option("--interval", type=float, default=1.0, help="Check interval in seconds")
@click.option("--timeout", type=float, help="Max watch time in seconds")
@click.option("--path", "-p", help="Output directory")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def watch(app, window_title, hwnd, interval, timeout, path, json_output):
    """Watch for screen changes and capture on change."""
    click.echo("Not implemented yet — coming in Phase 3")


# ── list ────────────────────────────────────────


@click.group("list")
def list_cmd():
    """List apps, windows, screens, or permissions."""
    pass


@list_cmd.command()
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def apps(json_output):
    """List running applications."""
    click.echo("Not implemented yet — coming in Phase 2")


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
        click.echo("Window listing requires Windows (naturo_core.dll).")
        return

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
            click.echo(json_module.dumps(data, indent=2))
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
    """List connected screens/monitors."""
    click.echo("Not implemented yet — coming in Phase 2")


@list_cmd.command()
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def permissions(json_output):
    """List automation permissions status (UIAccess, admin, etc.)."""
    click.echo("Not implemented yet — coming in Phase 2")


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
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def see(app, window_title, hwnd, pid, mode, depth, path, annotate, json_output):
    """Capture screenshot and analyze UI elements.

    Inspects the UI element tree of the foreground window (or a specific
    window identified by --hwnd). Shows the element hierarchy with roles,
    names, and bounding rectangles.
    """
    if platform.system() != "Windows":
        click.echo("UI inspection requires Windows (naturo_core.dll).")
        return

    try:
        backend = _get_backend()
        tree = backend.get_element_tree(depth=depth)

        if tree is None:
            click.echo("No window found or UI tree is empty.")
            return

        if json_output:
            def to_dict(el):
                """Convert ElementInfo tree to a JSON-serializable dict."""
                return {
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
            click.echo(json_module.dumps(to_dict(tree), indent=2))
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

        # Optionally capture screenshot
        if path:
            result = backend.capture_screen(output_path=path)
            click.echo(f"\nScreenshot saved: {result.path}")

    except Exception as e:
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
    else:
        click.echo("\nNaturo — Windows desktop automation engine\n")
        click.echo("Available topics:")
        for t, desc in topics.items():
            click.echo(f"  {t:15s} {desc}")
        click.echo("\nRun: naturo learn <topic> for details.")


# ── tools ───────────────────────────────────────


@click.command()
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def tools(json_output):
    """List available automation tools and backends.

    Shows which native backends are available (UIA, MSAA, Java Bridge, etc.).
    """
    click.echo("Not implemented yet — coming in Phase 2")
