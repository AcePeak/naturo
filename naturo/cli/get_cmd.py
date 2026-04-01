"""Get command — read element text/value via UIA patterns.

Reads the current value of a UI element by querying UIAutomation
patterns: ValuePattern, TogglePattern, SelectionPattern,
RangeValuePattern, and TextPattern.
"""
import json as json_module
import platform
import sys

import click

from naturo.cli.error_helpers import emit_error, emit_exception_error
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


def _collect_matching_elements(tree, role=None, name=None):
    """Walk the element tree and collect all elements matching role/name.

    Args:
        tree: Root ElementInfo from get_element_tree.
        role: Role filter (case-insensitive exact match). None matches any.
        name: Name filter (case-insensitive substring). None matches any.

    Returns:
        List of matching ElementInfo nodes.
    """
    matches = []

    def _walk(el, depth=0) -> None:
        role_match = role is None or el.role.lower() == role.lower()
        name_match = name is None or (
            el.name and name.lower() in el.name.lower()
        )
        if role_match and name_match:
            matches.append(el)
        for child in el.children:
            _walk(child, depth + 1)

    _walk(tree)
    return matches


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
@click.option("--all", "-a", "get_all", is_flag=True, default=False,
              help="Return all matching elements (requires --role or --name)")
@click.option("--property", "-p", "prop", default=None,
              help="Return only a specific property (value, name, role, pattern)")
@click.option("--app", default=None, help="Target application (name or partial match)")
@click.option("--app-id", "app_id", default=None,
              help='Stable app/window ID from "naturo app list" output (e.g. a1)')
@click.option("--window", "window_title", default=None,
              help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", default=None, type=int,
              help="Window handle (HWND)")
@click.option("--json", "-j", "json_output", is_flag=True, default=None,
              help="JSON output")
@click.pass_context
def get_cmd(ctx, target, ref, automation_id, role, name, get_all, prop, app,
            app_id, window_title, hwnd, json_output) -> None:
    """Read element text/value.

    Read the current value of a UI element. Accepts an element ref (e47),
    an AutomationId, or a role+name combination.

    Use --all to return all matching elements instead of just the first.
    Requires --role or --name to specify what to search for.

    \b
    Examples:
      naturo get e47                      # Read value by ref
      naturo get e47 --json               # JSON output
      naturo get --aid txtSearch          # By AutomationId
      naturo get --role Edit --name Search # By role + name
      naturo get e47 -p value             # Just the value text
      naturo get --role Button --app explorer --all -j  # All buttons
      naturo get --role Edit --all        # All edit fields
    """
    # Inherit --json from parent group if not set explicitly
    if json_output is None:
        json_output = ctx.obj.get("json", False) if ctx.obj else False

    # (#752) Auto-detect app ID pattern (a1, a2, ...) in --app flag
    from naturo.cli.options import maybe_promote_app_to_app_id
    app, app_id = maybe_promote_app_to_app_id(app, app_id)

    # (#522) Resolve --app-id to hwnd override (consistent with
    # see/click/capture/type which all accept --app-id).
    # (#582) Do NOT leak process_name as app — it may be a full path
    # that breaks fuzzy matching (same bug pattern as #576).
    if app_id is not None:
        from naturo.app_ids import get_app_id_map

        id_map = get_app_id_map()
        entry = id_map.resolve(app_id)
        if entry is None:
            emit_error(
                "APP_ID_NOT_FOUND",
                f'App ID "{app_id}" not found or expired. '
                f'Run "naturo app list" to refresh.',
                json_output,
            )
        hwnd = entry.handle

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

    # ── --all mode: return all matching elements ─────────────────────────
    if get_all:
        if not role and not name:
            emit_error(
                "INVALID_INPUT",
                "--all requires --role or --name to specify what to search for",
                json_output,
                suggested_action="Add --role (e.g. --role Button) or --name "
                "to filter which elements to return.",
            )

        if platform.system() not in ("Windows",) and not _has_peekaboo():
            emit_error(
                "PLATFORM_ERROR",
                "naturo get requires Windows (UIA patterns) or macOS (Peekaboo)",
                json_output,
            )

        try:
            backend = _get_backend()
            tree = backend.get_element_tree(
                app=app, window_title=window_title, hwnd=hwnd,
                depth=20, backend="auto",
            )

            if tree is None:
                emit_error(
                    "WINDOW_NOT_FOUND",
                    "No window found for the specified target",
                    json_output,
                    suggested_action="Check that the application is running "
                    "and visible.",
                )

            matches = _collect_matching_elements(tree, role=role, name=name)

            if json_output:
                output = []
                for el in matches:
                    output.append({
                        "role": el.role,
                        "name": el.name,
                        "value": el.value,
                        "x": el.x,
                        "y": el.y,
                        "width": el.width,
                        "height": el.height,
                    })
                click.echo(json_module.dumps(output))
            else:
                if not matches:
                    filters = []
                    if role:
                        filters.append(f"role={role}")
                    if name:
                        filters.append(f"name={name}")
                    click.echo(f"No elements found matching {', '.join(filters)}")
                    sys.exit(1)
                click.echo(f"Found {len(matches)} matching element(s):\n")
                for i, el in enumerate(matches, 1):
                    header = f"  {i}. [{el.role}]"
                    if el.name:
                        header += f' "{el.name}"'
                    header += f"  ({el.x},{el.y} {el.width}x{el.height})"
                    click.echo(header)
                    if el.value is not None:
                        preview = el.value[:100]
                        if len(el.value) > 100:
                            preview += "…"
                        click.echo(f"     Value: {preview}")

        except NaturoError as exc:
            emit_exception_error(exc, json_output)
        except Exception as exc:
            emit_exception_error(exc, json_output, fallback_code="UNKNOWN_ERROR")
        return

    # ── Single element mode (default) ────────────────────────────────────
    if not ref and not automation_id and not role and not name:
        emit_error(
            "INVALID_INPUT",
            "Specify a target: element ref (e47), --automation-id, or --role/--name",
            json_output,
            suggested_action="Provide a target element using a ref (e47), "
            "--automation-id, or --role/--name. Run 'naturo see' to inspect "
            "available elements.",
        )

    if platform.system() not in ("Windows",) and not _has_peekaboo():
        emit_error(
            "PLATFORM_ERROR",
            "naturo get requires Windows (UIA patterns) or macOS (Peekaboo)",
            json_output,
        )

    try:
        backend = _get_backend()
        result = backend.get_element_value(
            ref=ref,
            automation_id=automation_id,
            role=role,
            name=name,
            app=app,
            window_title=window_title,
            hwnd=hwnd,
        )

        if result is None:
            msg = "Element not found"
            if ref:
                msg += f" (ref={ref})"
            if automation_id:
                msg += f" (automation_id={automation_id})"
            if role:
                msg += f" (role={role})"
            suggested = (
                "Run 'naturo see' to inspect available elements and their "
                "actual roles.  Note: some apps use different role names "
                "than expected (e.g. Notepad uses 'Document' instead of "
                "'Edit' for its text area)."
            )
            emit_error(
                "ELEMENT_NOT_FOUND",
                msg,
                json_output,
                suggested_action=suggested,
            )

        if json_output:
            element_data = {
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
            click.echo(json_module.dumps(element_data))
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
        emit_exception_error(exc, json_output)
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="UNKNOWN_ERROR")


def _has_peekaboo() -> bool:
    """Check if Peekaboo CLI is available on macOS."""
    import shutil
    return shutil.which("peekaboo") is not None
