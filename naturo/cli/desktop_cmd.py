"""Virtual desktop CLI commands — list, switch, create, close, move windows.

Phase 5A.3: Virtual Desktop management for Windows 10/11.

Provides commands to enumerate virtual desktops, switch between them,
create/close desktops, and move windows across desktops.

Examples:
    naturo desktop list                       # List virtual desktops
    naturo desktop list --json                # JSON output
    naturo desktop switch 1                   # Switch to desktop index 1
    naturo desktop create --name "Work"       # Create named desktop
    naturo desktop close                      # Close current desktop
    naturo desktop close 2                    # Close desktop index 2
    naturo desktop move-window 1 --app "Notepad"  # Move Notepad to desktop 1
"""

from __future__ import annotations

import json as _json
import sys

import click as _click

from naturo.cli.error_helpers import emit_error, emit_exception_error
from naturo.cli.fuzzy_group import FuzzyGroup


def _ensure_pyvda() -> None:
    """Ensure pyvda is available, prompting to install if missing."""
    from naturo.deps import ensure_package
    ensure_package("pyvda", feature="Virtual desktop", install_extra="desktop")


@_click.group(cls=FuzzyGroup)
def desktop():
    """Virtual desktop management (Windows 10/11).

    List, switch, create, and close virtual desktops.
    Move windows between desktops.

    Windows equivalent of macOS Spaces / Peekaboo's space commands.

    \b
    Examples:
        naturo desktop list                    # List all desktops
        naturo desktop switch 1                # Switch to desktop 1
        naturo desktop create --name "Dev"     # Create a named desktop
        naturo desktop close                   # Close current desktop
        naturo desktop move-window 1 --app X   # Move app to desktop 1
    """
    pass


@desktop.command("list")
@_click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def desktop_list(json_output: bool) -> None:
    """List all virtual desktops.

    Shows each desktop's index, name, and whether it is the current
    active desktop.

    \b
    Examples:
        naturo desktop list                    # Human-readable list
        naturo desktop list --json             # JSON output
    """
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    try:
        _ensure_pyvda()
        backend = get_backend()
        desktops = backend.virtual_desktop_list()

        if json_output:
            _click.echo(_json.dumps({
                "success": True,
                "desktops": desktops,
                "count": len(desktops),
            }))
        else:
            if not desktops:
                _click.echo("No virtual desktops found.")
            else:
                for d in desktops:
                    current = " [current]" if d.get("is_current") else ""
                    _click.echo(f"  {d['index']}: {d['name']}{current}")

    except NaturoError as e:
        emit_exception_error(e, json_output)
    except SystemExit:
        raise
    except Exception as e:
        emit_exception_error(e, json_output, fallback_code="VIRTUAL_DESKTOP_ERROR")


@desktop.command("switch")
@_click.argument("index", type=int)
@_click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def desktop_switch(index: int, json_output: bool) -> None:
    """Switch to a virtual desktop by index.

    INDEX is the zero-based desktop number (from 'desktop list').

    \b
    Examples:
        naturo desktop switch 0               # Switch to first desktop
        naturo desktop switch 2               # Switch to third desktop
        naturo desktop switch 1 --json        # JSON output
    """
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    if index < 0:
        emit_error(
            "INVALID_INPUT",
            f"Desktop index must be >= 0, got {index}",
            json_output,
        )

    try:
        _ensure_pyvda()
        backend = get_backend()
        result = backend.virtual_desktop_switch(index)

        if json_output:
            _click.echo(_json.dumps({"success": True, **result}))
        else:
            _click.echo(f"Switched to desktop {result['index']}: {result['name']}")

    except NaturoError as e:
        emit_exception_error(e, json_output)
    except SystemExit:
        raise
    except Exception as e:
        emit_exception_error(e, json_output, fallback_code="VIRTUAL_DESKTOP_ERROR")


@desktop.command("create")
@_click.option("--name", default=None, help="Name for the new desktop")
@_click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def desktop_create(name: str | None, json_output: bool) -> None:
    """Create a new virtual desktop.

    Optionally assign a NAME. If omitted, Windows assigns a default name.

    \b
    Examples:
        naturo desktop create                  # Create unnamed desktop
        naturo desktop create --name "Work"    # Create named desktop
        naturo desktop create --json           # JSON output
    """
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    try:
        _ensure_pyvda()
        backend = get_backend()
        result = backend.virtual_desktop_create(name=name)

        if json_output:
            _click.echo(_json.dumps({"success": True, **result}))
        else:
            _click.echo(f"Created desktop {result['index']}: {result['name']}")

    except NaturoError as e:
        emit_exception_error(e, json_output)
    except SystemExit:
        raise
    except Exception as e:
        emit_exception_error(e, json_output, fallback_code="VIRTUAL_DESKTOP_ERROR")


@desktop.command("close")
@_click.argument("index", type=int, required=False, default=None)
@_click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def desktop_close(index: int | None, json_output: bool) -> None:
    """Close a virtual desktop.

    Without INDEX, closes the current desktop. With INDEX, closes that
    specific desktop. Cannot close the last remaining desktop.

    \b
    Examples:
        naturo desktop close                   # Close current desktop
        naturo desktop close 2                 # Close desktop index 2
        naturo desktop close --json            # JSON output
    """
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    if index is not None and index < 0:
        emit_error(
            "INVALID_INPUT",
            f"Desktop index must be >= 0, got {index}",
            json_output,
        )

    try:
        _ensure_pyvda()
        backend = get_backend()
        result = backend.virtual_desktop_close(index=index)

        if json_output:
            _click.echo(_json.dumps({"success": True, **result}))
        else:
            _click.echo(f"Closed desktop {result['index']}: {result['name']}")

    except NaturoError as e:
        emit_exception_error(e, json_output)
    except SystemExit:
        raise
    except Exception as e:
        emit_exception_error(e, json_output, fallback_code="VIRTUAL_DESKTOP_ERROR")


@desktop.command("move-window")
@_click.argument("index", type=int)
@_click.option("--app", default=None, help="Application name (partial match)")
@_click.option("--hwnd", type=int, default=None, help="Window handle")
@_click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def desktop_move_window(
    index: int,
    app: str | None,
    hwnd: int | None,
    json_output: bool,
) -> None:
    """Move a window to a different virtual desktop.

    INDEX is the target desktop (zero-based). Identify the window by
    --app name or --hwnd handle. If neither is given, moves the
    foreground window.

    \b
    Examples:
        naturo desktop move-window 1 --app "Notepad"    # Move Notepad
        naturo desktop move-window 0 --hwnd 12345       # Move by handle
        naturo desktop move-window 2                    # Move foreground
        naturo desktop move-window 1 --app X --json     # JSON output
    """
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    if index < 0:
        emit_error(
            "INVALID_INPUT",
            f"Desktop index must be >= 0, got {index}",
            json_output,
        )

    try:
        _ensure_pyvda()
        backend = get_backend()
        result = backend.virtual_desktop_move_window(
            desktop_index=index,
            app=app,
            hwnd=hwnd,
        )

        if json_output:
            _click.echo(_json.dumps({"success": True, **result}))
        else:
            target = result.get("target_name", f"Desktop {index}")
            _click.echo(f"Moved window to {target}")

    except NaturoError as e:
        emit_exception_error(e, json_output)
    except SystemExit:
        raise
    except Exception as e:
        emit_exception_error(e, json_output, fallback_code="VIRTUAL_DESKTOP_ERROR")
