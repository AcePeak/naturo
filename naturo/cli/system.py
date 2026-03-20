"""System commands: app, window, menu, clipboard, dialog, open, taskbar, tray, desktop."""
import click

# ── app ─────────────────────────────────────────


@click.group()
def app():
    """Manage applications: launch, quit, switch, and more."""
    pass


@app.command(hidden=True)
@click.argument("name")
@click.option("--args", multiple=True, help="Launch arguments")
@click.option("--wait", is_flag=True, help="Wait for app to start")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def launch(name, args, wait, json_output):
    """Launch an application by name or path."""
    click.echo("Not implemented yet — coming in Phase 2")


@app.command(hidden=True)
@click.argument("name")
@click.option("--pid", type=int, help="Process ID")
@click.option("--force", is_flag=True, help="Force kill")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def quit(name, pid, force, json_output):
    """Quit an application gracefully (or force kill)."""
    click.echo("Not implemented yet — coming in Phase 2")


@app.command(hidden=True)
@click.argument("name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def relaunch(name, json_output):
    """Quit and relaunch an application."""
    click.echo("Not implemented yet — coming in Phase 2")



@app.command(name="list", hidden=True)
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def app_list(json_output):
    """List running applications."""
    click.echo("Not implemented yet — coming in Phase 2")



# ── menu ────────────────────────────────────────


@click.group()
def menu():
    """Interact with application menu bars."""
    pass


@menu.command(name="click")
@click.argument("path")
@click.option("--app", help="Application name")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def menu_click(path, app, window_title, hwnd, json_output):
    """Click a menu item by path (e.g. 'File > Save As')."""
    click.echo("Not implemented yet — coming in Phase 3")


@menu.command(name="list")
@click.option("--app", help="Application name")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle")
@click.option("--depth", type=int, default=3, help="Menu tree depth")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def menu_list(app, window_title, hwnd, depth, json_output):
    """List menu items of an application."""
    click.echo("Not implemented yet — coming in Phase 3")


# ── clipboard ───────────────────────────────────


@click.group()
def clipboard():
    """Get or set clipboard text content.

    Examples:
        naturo clipboard get                  # Print clipboard text
        naturo clipboard get --json           # JSON output
        naturo clipboard set "Hello World"    # Set clipboard text
        naturo clipboard set --file note.txt  # Set clipboard from file
    """
    pass


@clipboard.command()
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def get(json_output):
    """Get clipboard text content.

    Retrieves the current text content from the system clipboard.

    Examples:
        naturo clipboard get          # Print clipboard text to stdout
        naturo clipboard get --json   # {"success": true, "text": "..."}
    """
    import json as _json
    import sys
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    try:
        backend = get_backend()
        text = backend.clipboard_get()
        if json_output:
            click.echo(_json.dumps({"success": True, "text": text}))
        else:
            click.echo(text, nl=False)
    except NaturoError as e:
        if json_output:
            click.echo(_json.dumps({
                "success": False,
                "error": {"code": e.code, "message": e.message},
            }))
        else:
            click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)
    except Exception as e:
        if json_output:
            click.echo(_json.dumps({
                "success": False,
                "error": {"code": "UNKNOWN_ERROR", "message": str(e)},
            }))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@clipboard.command("set")
@click.argument("content", required=False)
@click.option("--file", "file_path", type=click.Path(), help="Set clipboard from file content")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def clipboard_set(content, file_path, json_output):
    """Set clipboard text content.

    Provide text as an argument, or use --file to read from a file.
    If neither is given, reads from stdin.

    Args:
        content: Text to copy to clipboard.

    Examples:
        naturo clipboard set "Hello World"       # Set from argument
        naturo clipboard set --file readme.txt   # Set from file
        echo "piped" | naturo clipboard set      # Set from stdin
    """
    import json as _json
    import sys
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    # Determine text source: argument > --file > stdin
    if content is not None and file_path is not None:
        if json_output:
            click.echo(_json.dumps({
                "success": False,
                "error": {"code": "INVALID_INPUT", "message": "Specify text or --file, not both."},
            }))
        else:
            click.echo("Error: Specify text or --file, not both.", err=True)
        sys.exit(1)

    text: str
    if content is not None:
        text = content
    elif file_path is not None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            if json_output:
                click.echo(_json.dumps({
                    "success": False,
                    "error": {"code": "FILE_ERROR", "message": str(e)},
                }))
            else:
                click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    elif not sys.stdin.isatty():
        text = sys.stdin.read()
    else:
        if json_output:
            click.echo(_json.dumps({
                "success": False,
                "error": {"code": "INVALID_INPUT", "message": "No content provided. Pass text, --file, or pipe stdin."},
            }))
        else:
            click.echo("Error: No content provided. Pass text, --file, or pipe stdin.", err=True)
        sys.exit(1)

    try:
        backend = get_backend()
        backend.clipboard_set(text)
        if json_output:
            click.echo(_json.dumps({"success": True, "length": len(text)}))
        else:
            click.echo(f"Clipboard set ({len(text)} chars)")
    except NaturoError as e:
        if json_output:
            click.echo(_json.dumps({
                "success": False,
                "error": {"code": e.code, "message": e.message},
            }))
        else:
            click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)
    except Exception as e:
        if json_output:
            click.echo(_json.dumps({
                "success": False,
                "error": {"code": "UNKNOWN_ERROR", "message": str(e)},
            }))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ── dialog ──────────────────────────────────────


@click.command()
@click.option("--action", type=click.Choice(["accept", "dismiss", "type"]),
              help="Action to perform on dialog")
@click.option("--text", help="Text to type in dialog input")
@click.option("--button", help="Button to click")
@click.option("--app", help="Application name")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle")
@click.option("--wait", type=float, help="Wait for dialog (seconds)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def dialog(action, text, button, app, window_title, hwnd, wait, json_output):
    """Interact with system dialogs (file picker, message box, etc.)."""
    click.echo("Not implemented yet — coming in Phase 3")


# ── open ────────────────────────────────────────


@click.command("open")
@click.argument("target")
@click.option("--app", help="Open with specific application")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def open_cmd(target, app, json_output):
    """Open a URL or file with default or specified application.

    Examples:
        naturo open https://example.com       # Open URL in browser
        naturo open C:\\readme.txt             # Open file with default app
        naturo open document.pdf --app acrobat
    """
    import json as _json
    import sys
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    try:
        backend = get_backend()
        # TODO: --app option for opening with specific application
        backend.open_uri(uri=target)
        if json_output:
            click.echo(_json.dumps({"success": True, "target": target}))
        else:
            click.echo(f"Opened: {target}")
    except NaturoError as e:
        if json_output:
            from naturo.cli.error_helpers import json_error_from_exception
            click.echo(json_error_from_exception(e))
        else:
            click.echo(f"Error: {e.message}", err=True)
        sys.exit(1)
    except Exception as e:
        if json_output:
            from naturo.cli.error_helpers import json_error
            click.echo(json_error("UNKNOWN_ERROR", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# ── taskbar (Windows-specific, maps to Peekaboo dock) ──


@click.group()
def taskbar():
    """Windows taskbar management (pin, unpin, list).

    Windows equivalent of Peekaboo's dock commands.
    """
    pass


@taskbar.command()
@click.argument("name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def pin(name, json_output):
    """Pin an application to the taskbar."""
    click.echo("Not implemented yet — coming in Phase 3")


@taskbar.command()
@click.argument("name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def unpin(name, json_output):
    """Unpin an application from the taskbar."""
    click.echo("Not implemented yet — coming in Phase 3")


@taskbar.command(name="list")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def taskbar_list(json_output):
    """List taskbar pinned items."""
    click.echo("Not implemented yet — coming in Phase 3")


# ── tray (Windows-specific, maps to Peekaboo menubar) ──


@click.group()
def tray():
    """System tray icon interaction.

    Windows equivalent of Peekaboo's menubar commands.
    """
    pass


@tray.command(name="list")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def tray_list(json_output):
    """List system tray icons."""
    click.echo("Not implemented yet — coming in Phase 3")


@tray.command(name="click")
@click.argument("name")
@click.option("--double", is_flag=True, help="Double-click")
@click.option("--right", is_flag=True, help="Right-click")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def tray_click(name, double, right, json_output):
    """Click a system tray icon by name."""
    click.echo("Not implemented yet — coming in Phase 3")


# ── desktop (Windows-specific, maps to Peekaboo space) ──


@click.group()
def desktop():
    """Virtual desktop management.

    Windows equivalent of Peekaboo's space commands.
    """
    pass


@desktop.command(name="list")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def desktop_list(json_output):
    """List virtual desktops."""
    click.echo("Not implemented yet — coming in Phase 3")


@desktop.command()
@click.option("--name", help="Name for the new desktop")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def create(name, json_output):
    """Create a new virtual desktop."""
    click.echo("Not implemented yet — coming in Phase 3")


@desktop.command(name="switch")
@click.argument("target")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def desktop_switch(target, json_output):
    """Switch to a virtual desktop by index or name."""
    click.echo("Not implemented yet — coming in Phase 3")


@desktop.command(name="close")
@click.argument("target", required=False)
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def desktop_close(target, json_output):
    """Close a virtual desktop."""
    click.echo("Not implemented yet — coming in Phase 3")
