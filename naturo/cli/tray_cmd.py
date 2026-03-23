"""System tray CLI commands — list and interact with tray icons.

Phase 4.5.5: System Tray Interaction.

Provides commands to list notification area icons and click them
to interact with background applications.

Examples:
    naturo tray list                         # List tray icons
    naturo tray list --json                  # JSON output
    naturo tray click "Volume"               # Left-click volume icon
    naturo tray click "Wi-Fi" --right        # Right-click for menu
    naturo tray click "Dropbox" --double     # Double-click to open
"""

from __future__ import annotations

import json as _json
import sys

import click as _click

from naturo.cli.error_helpers import emit_error, emit_exception_error


@_click.group()
def tray():
    """Interact with the system tray (notification area).

    List icons in the Windows notification area and click them to
    interact with background applications.

    \b
    Examples:
        naturo tray list                       # List all tray icons
        naturo tray click "Volume"             # Left-click Volume
        naturo tray click "Wi-Fi" --right      # Right-click for menu
    """
    pass


@tray.command("list")
@_click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def tray_list(json_output):
    """List system tray icons.

    Shows icons in the Windows notification area (system tray), including
    both visible icons and those in the overflow panel.

    \b
    Examples:
        naturo tray list                       # Human-readable list
        naturo tray list --json                # JSON output
    """
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    try:
        backend = get_backend()
        icons = backend.tray_list()

        if json_output:
            _click.echo(_json.dumps({
                "success": True,
                "icons": icons,
                "count": len(icons),
            }))
        else:
            if not icons:
                _click.echo("No tray icons found.")
            else:
                for icon in icons:
                    visible = "" if icon.get("is_visible") else " [hidden]"
                    tooltip = f" — {icon['tooltip']}" if icon.get("tooltip") and icon["tooltip"] != icon["name"] else ""
                    _click.echo(f"  {icon['name']}{tooltip}{visible}")

    except NaturoError as e:
        emit_exception_error(e, json_output)
    except Exception as e:
        emit_exception_error(e, json_output, fallback_code="UNKNOWN_ERROR")


@tray.command("click")
@_click.argument("name")
@_click.option("--right", "right_click", is_flag=True, help="Right-click (context menu)")
@_click.option("--double", "double_click", is_flag=True, help="Double-click (open)")
@_click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def tray_click(name, right_click, double_click, json_output):
    """Click a system tray icon.

    Finds a tray icon matching NAME (case-insensitive, partial match)
    and clicks it. Use --right for context menus, --double to open.

    \b
    Examples:
        naturo tray click "Volume"             # Left-click
        naturo tray click "Wi-Fi" --right      # Right-click for menu
        naturo tray click "Dropbox" --double   # Double-click to open
    """
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    if not name.strip():
        emit_error("INVALID_INPUT", "Name cannot be empty", json_output)

    button = "right" if right_click else "left"

    try:
        backend = get_backend()
        result = backend.tray_click(name=name, button=button, double=double_click)

        if json_output:
            _click.echo(_json.dumps({"success": True, **result}))
        else:
            action = "Double-clicked" if double_click else ("Right-clicked" if right_click else "Clicked")
            _click.echo(f"{action} tray icon '{result['name']}'")

    except NaturoError as e:
        emit_exception_error(e, json_output)
    except SystemExit:
        raise
    except Exception as e:
        emit_exception_error(e, json_output, fallback_code="UNKNOWN_ERROR")
