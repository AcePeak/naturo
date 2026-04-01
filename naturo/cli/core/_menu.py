"""Menu-inspect command — list menu bar structure."""
from __future__ import annotations

import json as json_module

import click

import naturo.cli.core._common as _common


@click.command("menu_cmd")
@click.option("--app", help="Application name")
@click.option("--app-id", "app_id", default=None,
              help='Stable app/window ID from "naturo app list" output (e.g. a1)')
@click.option("--flat", is_flag=True, help="Flatten menu tree into paths")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def menu_inspect(app, app_id, flat, json_output) -> None:
    """List the menu bar structure of the foreground application.

    Traverses the application's MenuBar via UIAutomation and displays
    all menu items with their keyboard shortcuts.

    \b
    Examples:
      naturo menu-inspect                     # Foreground app
      naturo menu-inspect --app notepad       # Specific app
      naturo menu-inspect --flat              # Flat path list
      naturo menu-inspect --app notepad --json # JSON output
    """
    # (#752) Auto-detect app ID pattern (a1, a2, ...) in --app flag
    from naturo.cli.options import maybe_promote_app_to_app_id
    app, app_id = maybe_promote_app_to_app_id(app, app_id)

    # (#593) Resolve --app-id to hwnd before any other logic
    hwnd = None
    if app_id is not None:
        from naturo.app_ids import get_app_id_map
        id_map = get_app_id_map()
        entry = id_map.resolve(app_id)
        if entry is None:
            msg = f'App ID "{app_id}" not found or expired. Run "naturo app list" to refresh.'
            if json_output:
                click.echo(_common._json_error_str("APP_ID_NOT_FOUND", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
            raise SystemExit(1)
        hwnd = entry.handle

    if not _common._platform_supports_gui():
        msg = _common._platform_error_msg("Menu inspection")
        if json_output:
            click.echo(_common._json_error_str("PLATFORM_ERROR", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)

    try:
        backend = _common._get_backend(json_output)

        # BUG-026: Check if app exists before inspecting menus
        if app:
            try:
                from naturo.process import find_process
                app_info = find_process(app)
                if not app_info:
                    msg = f"Application not found: {app}"
                    if json_output:
                        click.echo(_common._json_error_str("APP_NOT_FOUND", msg))
                    else:
                        click.echo(f"Error: {msg}", err=True)
                    raise SystemExit(1)
            except ImportError:
                pass  # find_process not available, fall through to get_menu_items
            except SystemExit:
                raise
            except Exception:
                pass  # find_process failed for other reasons, fall through

        items = backend.get_menu_items(window_title=app, hwnd=hwnd)

        if not items:
            msg = "No menu items found."
            if json_output:
                click.echo(_common._json_error_str("NO_MENU_ITEMS", msg))
            else:
                click.echo(f"Error: {msg}", err=True)
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
                def print_menu(item, indent=0) -> None:
                    """Recursively print a menu item and its submenus with indentation."""
                    prefix = "  " * indent
                    shortcut = f" [{item.shortcut}]" if item.shortcut else ""
                    state = ""
                    if not item.enabled:
                        state += " (disabled)"
                    if item.checked:
                        state += " (\u2713)"
                    click.echo(f"{prefix}{item.name}{shortcut}{state}")
                    if item.submenu:
                        for sub in item.submenu:
                            print_menu(sub, indent + 1)

                for item in items:
                    print_menu(item)

    except NotImplementedError:
        msg = "Menu inspection not supported on this platform."
        if json_output:
            click.echo(_common._json_error_str("NOT_SUPPORTED", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)
    except Exception as e:
        if json_output:
            click.echo(_common._json_error_str("UNKNOWN_ERROR", str(e)))
        else:
            click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
