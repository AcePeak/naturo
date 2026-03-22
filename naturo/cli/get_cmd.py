"""Get command — read element text/value via UIA patterns.

Reads the current value of a UI element by querying UIAutomation
patterns: ValuePattern, TogglePattern, SelectionPattern,
RangeValuePattern, and TextPattern.
"""
import json as json_module
import platform
import sys

import click

from naturo.cli.error_helpers import json_error as _json_error_str
from naturo.errors import NaturoError


def _get_backend():
    """Get the platform-appropriate backend.

    Returns:
        A Backend instance for the current platform.

    Raises:
        RuntimeError: If no backend is available.
    """
    from naturo.backends.base import get_backend
    return get_backend()


@click.command("get")
@click.argument("target", required=False)
@click.option("--ref", "-r", "ref", default=None,
              help="Element ref from snapshot (e.g. e47)")
@click.option("--automation-id", "--aid", "automation_id", default=None,
              help="UIA AutomationId of the target element")
@click.option("--role", default=None,
              help="Element role filter (e.g. Edit, Button)")
@click.option("--name", default=None,
              help="Element name filter")
@click.option("--property", "-p", "prop", default=None,
              help="Return only a specific property (value, name, role, pattern)")
@click.option("--app", default=None, help="Target application name")
@click.option("--window-title", "--title", default=None,
              help="Target window title (partial match)")
@click.option("--hwnd", default=None, type=int,
              help="Target window handle")
@click.option("--json", "-j", "json_output", is_flag=True, default=None,
              help="JSON output")
@click.pass_context
def get_cmd(ctx, target, ref, automation_id, role, name, prop, app,
            window_title, hwnd, json_output):
    """Read element text/value.

    Read the current value of a UI element. Accepts an element ref (e47),
    an AutomationId, or a role+name combination.

    \b
    Examples:
      naturo get e47                      # Read value by ref
      naturo get e47 --json               # JSON output
      naturo get --aid txtSearch          # By AutomationId
      naturo get --role Edit --name Search # By role + name
      naturo get e47 -p value             # Just the value text
    """
    # Inherit --json from parent group if not set explicitly
    if json_output is None:
        json_output = ctx.obj.get("json", False) if ctx.obj else False

    # Parse target argument: could be a ref (e47) or an automation ID
    if target:
        if target.startswith("e") and target[1:].isdigit():
            if not ref:
                ref = target
        elif target.startswith("m") and target[1:].isdigit():
            if not ref:
                ref = target
        elif target.startswith("a") and target[1:].isdigit():
            if not ref:
                ref = target
        elif target.startswith("j") and target[1:].isdigit():
            if not ref:
                ref = target
        else:
            # Treat as automation ID
            if not automation_id:
                automation_id = target

    if not ref and not automation_id and not role and not name:
        msg = "Specify a target: element ref (e47), --automation-id, or --role/--name"
        if json_output:
            click.echo(json_module.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    if platform.system() not in ("Windows",) and not _has_peekaboo():
        msg = "naturo get requires Windows (UIA patterns) or macOS (Peekaboo)"
        if json_output:
            click.echo(json_module.dumps({"error": msg}))
        else:
            click.echo(f"Error: {msg}", err=True)
        sys.exit(1)

    try:
        backend = _get_backend()
        result = backend.get_element_value(
            ref=ref,
            automation_id=automation_id,
            role=role,
            name=name,
            window_title=window_title,
            hwnd=hwnd,
        )

        if result is None:
            msg = f"Element not found"
            if ref:
                msg += f" (ref={ref})"
            if automation_id:
                msg += f" (automation_id={automation_id})"
            if json_output:
                click.echo(json_module.dumps({"error": msg, "found": False}))
            else:
                click.echo(f"Error: {msg}", err=True)
            sys.exit(1)

        if json_output:
            output = {
                "ref": ref,
                "role": result.get("role"),
                "name": result.get("name"),
                "value": result.get("value"),
                "pattern": result.get("pattern"),
                "automation_id": result.get("automation_id"),
                "x": result.get("x"),
                "y": result.get("y"),
                "width": result.get("width"),
                "height": result.get("height"),
            }
            click.echo(json_module.dumps(output))
        elif prop:
            # Return just the requested property
            val = result.get(prop)
            if val is not None:
                click.echo(val)
            else:
                click.echo(f"Property '{prop}' is null or not available",
                           err=True)
                sys.exit(1)
        else:
            # Plain text output
            value = result.get("value")
            role_str = result.get("role", "")
            name_str = result.get("name", "")
            pattern = result.get("pattern")

            header = f"[{role_str}]"
            if name_str:
                header += f' "{name_str}"'
            if ref:
                header += f" {ref}"

            click.echo(header)
            if value is not None:
                click.echo(f"Value: {value}")
            else:
                click.echo("Value: (none — no readable pattern)")
            if pattern:
                click.echo(f"Pattern: {pattern}")

    except NaturoError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)
    except Exception as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        sys.exit(1)


def _has_peekaboo() -> bool:
    """Check if Peekaboo CLI is available on macOS."""
    import shutil
    return shutil.which("peekaboo") is not None
