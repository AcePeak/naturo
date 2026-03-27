"""Taskbar CLI commands — list and interact with taskbar items.

Phase 4.5.4: Taskbar Interaction.

Provides commands to list running/pinned taskbar items and click them
to activate the corresponding application window.

Examples:
    naturo taskbar list                      # List taskbar items
    naturo taskbar list --json               # JSON output
    naturo taskbar click "Chrome"            # Click Chrome on taskbar
    naturo taskbar click "Chrome" --json     # JSON output
"""

from __future__ import annotations

import json as _json

import click as _click

from naturo.cli.error_helpers import emit_error, emit_exception_error


@_click.group()
def taskbar():
    """Interact with the Windows taskbar.

    List running applications and pinned shortcuts on the taskbar,
    and click items to activate windows.

    \b
    Examples:
        naturo taskbar list                    # List all taskbar items
        naturo taskbar list --json             # JSON output
        naturo taskbar click "Notepad"         # Activate Notepad
    """
    pass


@taskbar.command("list")
@_click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def taskbar_list(json_output):
    """List items on the taskbar.

    Shows running applications and pinned shortcuts visible on the
    Windows taskbar. Each item includes name, active state, and position.

    \b
    Examples:
        naturo taskbar list                    # Human-readable list
        naturo taskbar list --json             # JSON output
    """
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    try:
        backend = get_backend()
        items = backend.taskbar_list()

        if json_output:
            _click.echo(_json.dumps({
                "success": True,
                "items": items,
                "count": len(items),
            }))
        else:
            if not items:
                _click.echo("No taskbar items found.")
            else:
                for item in items:
                    active = " [active]" if item.get("is_active") else ""
                    pinned = " [pinned]" if item.get("is_pinned") else ""
                    _click.echo(f"  {item['name']}{active}{pinned}")

    except NaturoError as e:
        emit_exception_error(e, json_output)
    except Exception as e:
        emit_exception_error(e, json_output, fallback_code="UNKNOWN_ERROR")


@taskbar.command("click")
@_click.argument("name")
@_click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def taskbar_click(name, json_output):
    """Click a taskbar item to activate its window.

    Finds a taskbar button matching NAME (case-insensitive, partial match)
    and clicks it to bring the application to the foreground.

    \b
    Examples:
        naturo taskbar click "Chrome"          # Activate Chrome
        naturo taskbar click "Notepad" --json  # JSON output
    """
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    if not name.strip():
        emit_error("INVALID_INPUT", "Name cannot be empty", json_output)

    try:
        backend = get_backend()
        result = backend.taskbar_click(name=name)

        if json_output:
            _click.echo(_json.dumps({"success": True, **result}))
        else:
            _click.echo(f"Clicked taskbar item '{result['name']}'")

    except NaturoError as e:
        emit_exception_error(e, json_output)
    except SystemExit:
        raise
    except Exception as e:
        emit_exception_error(e, json_output, fallback_code="UNKNOWN_ERROR")
