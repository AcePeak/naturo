"""System commands: app.

Note: dialog commands moved to naturo/cli/dialog_cmd.py (Phase 4.5).
Note: clipboard and open commands removed — handled by AI agent directly.
"""
import click
from naturo.cli.fuzzy_group import FuzzyGroup

# ── app ─────────────────────────────────────────


@click.group(cls=FuzzyGroup)
def app() -> None:
    """Manage applications and windows: launch, quit, focus, close, minimize, maximize, restore, move, and more."""
    pass


@app.command(hidden=True)
@click.argument("name")
@click.option("--args", multiple=True, help="Launch arguments")
@click.option("--wait", is_flag=True, help="Wait for app to start")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def launch(name, args, wait, json_output) -> None:
    """Launch an application by name or path."""
    click.echo("Not implemented yet. See 'naturo app --help' for available commands.")


@app.command(hidden=True)
@click.argument("name")
@click.option("--pid", type=int, help="Process ID")
@click.option("--force", is_flag=True, help="Force kill")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def quit(name, pid, force, json_output) -> None:
    """Quit an application gracefully (or force kill)."""
    click.echo("Not implemented yet. See 'naturo app --help' for available commands.")


@app.command(hidden=True)
@click.argument("name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def relaunch(name, json_output) -> None:
    """Quit and relaunch an application."""
    click.echo("Not implemented yet. See 'naturo app --help' for available commands.")


@app.command(name="list", hidden=True)
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def app_list(json_output) -> None:
    """List running applications."""
    click.echo("Not implemented yet. See 'naturo app --help' for available commands.")


# ── menu ────────────────────────────────────────


@click.group(cls=FuzzyGroup)
def menu() -> None:
    """Interact with application menu bars."""
    pass


@menu.command(name="click")
@click.argument("path")
@click.option("--app", help="Target application (name or partial match)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def menu_click(path, app, window_title, hwnd, json_output) -> None:
    """Click a menu item by path (e.g. 'File > Save As')."""
    click.echo("Not implemented yet. This feature is planned for a future release.")


@menu.command(name="list")
@click.option("--app", help="Target application (name or partial match)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--depth", type=int, default=3, help="Menu tree depth")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def menu_list(app, window_title, hwnd, depth, json_output) -> None:
    """List menu items of an application."""
    click.echo("Not implemented yet. This feature is planned for a future release.")


# ── taskbar (Windows-specific, maps to Peekaboo dock) ──


@click.group(cls=FuzzyGroup)
def taskbar() -> None:
    """Windows taskbar management (pin, unpin, list).

    Windows equivalent of Peekaboo's dock commands.
    """
    pass


@taskbar.command()
@click.argument("name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def pin(name, json_output) -> None:
    """Pin an application to the taskbar."""
    click.echo("Not implemented yet. This feature is planned for a future release.")


@taskbar.command()
@click.argument("name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def unpin(name, json_output) -> None:
    """Unpin an application from the taskbar."""
    click.echo("Not implemented yet. This feature is planned for a future release.")


@taskbar.command(name="list")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def taskbar_list(json_output) -> None:
    """List taskbar pinned items."""
    click.echo("Not implemented yet. This feature is planned for a future release.")


# ── tray (Windows-specific, maps to Peekaboo menubar) ──


@click.group(cls=FuzzyGroup)
def tray() -> None:
    """System tray icon interaction.

    Windows equivalent of Peekaboo's menubar commands.
    """
    pass


@tray.command(name="list")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def tray_list(json_output) -> None:
    """List system tray icons."""
    click.echo("Not implemented yet. This feature is planned for a future release.")


@tray.command(name="click")
@click.argument("name")
@click.option("--double", is_flag=True, help="Double-click")
@click.option("--right", is_flag=True, help="Right-click")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def tray_click(name, double, right, json_output) -> None:
    """Click a system tray icon by name."""
    click.echo("Not implemented yet. This feature is planned for a future release.")


# ── desktop — moved to naturo/cli/desktop_cmd.py (Phase 5A.3) ──
