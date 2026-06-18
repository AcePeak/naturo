"""Set command — write element value via UIA patterns.

Sets the value of a UI element using UIAutomation patterns:
ValuePattern (text fields), TogglePattern (checkboxes),
SelectionItemPattern (list/radio items), and ExpandCollapsePattern
(combo boxes).
"""
import json as json_module
import platform

import click

from naturo.cli.error_helpers import emit_error, emit_exception_error
from naturo.errors import NaturoError, StaleSnapshotCacheError


def _get_backend():
    """Get the platform-appropriate backend.

    Returns:
        A Backend instance for the current platform.

    Raises:
        RuntimeError: If no backend is available.
    """
    from naturo.backends.base import get_backend
    return get_backend()


def _resolve_element_identifiers(ref, automation_id, role, name):
    """Resolve a snapshot ref to element identifiers.

    Args:
        ref: Element ref from snapshot (e.g. ``"e47"``).
        automation_id: UIA AutomationId (passthrough if already set).
        role: Element role (passthrough if already set).
        name: Element name (passthrough if already set).

    Returns:
        Tuple of (automation_id, role, name) with ref resolved.

    Raises:
        NaturoError: If ref cannot be resolved.
    """
    if ref and not automation_id:
        from naturo.snapshot import get_snapshot_manager
        mgr = get_snapshot_manager()
        result = mgr.resolve_ref_element(ref)
        if result:
            elem, _snap_id = result
            if elem.identifier:
                automation_id = elem.identifier
            elif elem.role and (elem.title or elem.label):
                role = role or elem.role
                name = name or elem.title or elem.label
            else:
                raise NaturoError(
                    f"Element {ref} has no AutomationId, role, or name "
                    f"for value setting"
                )
        else:
            raise StaleSnapshotCacheError(ref)
    return automation_id, role, name


@click.command("set")
@click.argument("target", required=False)
@click.argument("value", required=False)
@click.option("--ref", "-r", "ref", default=None,
              help="Element ref from snapshot (e.g. e47)")
@click.option("--automation-id", "--aid", "automation_id", default=None,
              help="UIA AutomationId of the target element")
@click.option("--role", default=None,
              help="Element role filter (e.g. Edit, CheckBox)")
@click.option("--name", default=None,
              help="Element name filter")
@click.option("--toggle", is_flag=True, default=False,
              help="Toggle a checkbox or toggle button (TogglePattern)")
@click.option("--select", is_flag=True, default=False,
              help="Select a list item or radio button (SelectionItemPattern)")
@click.option("--expand", is_flag=True, default=False,
              help="Expand a combo box or tree item (ExpandCollapsePattern)")
@click.option("--collapse", is_flag=True, default=False,
              help="Collapse a combo box or tree item (ExpandCollapsePattern)")
@click.option("--app", default=None,
              help="Target application (name or partial match)")
@click.option("--app-id", "app_id", default=None,
              help='Stable app/window ID from "naturo app list" output (e.g. a1)')
@click.option("--window", "window_title", default=None,
              help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True,
              help="")
@click.option("--title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", default=None, type=int,
              help="Window handle (HWND)")
@click.option("--json", "-j", "json_output", is_flag=True, default=None,
              help="JSON output")
@click.pass_context
def set_cmd(ctx, target, value, ref, automation_id, role, name, toggle,
            select, expand, collapse, app, app_id, window_title, hwnd,
            json_output) -> None:
    """Set element value/state.

    Write a value to a UI element, toggle a checkbox, select a list item,
    or expand/collapse a combo box. Accepts an element ref (e47),
    an AutomationId, or a role+name combination.

    \b
    Examples:
      naturo set e47 "hello world"       # Set text field value
      naturo set --aid txtSearch "query"  # Set by AutomationId
      naturo set e12 --toggle            # Toggle a checkbox
      naturo set e8 --select             # Select a list/radio item
      naturo set e5 --expand             # Expand a combo box
      naturo set e5 --collapse           # Collapse a combo box
      naturo set --role Edit --name Search "test" --app notepad
    """
    if json_output is None:
        json_output = ctx.obj.get("json", False) if ctx.obj else False

    # (#752) Auto-detect app ID pattern (a1, a2, ...) in --app flag
    from naturo.cli.options import maybe_promote_app_to_app_id
    app, app_id = maybe_promote_app_to_app_id(app, app_id)

    # (#582) Resolve --app-id to hwnd override.
    # Use hwnd only, not process_name (avoids #576 full-path bug).
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

    # Parse positional arguments.  Click gives us [TARGET] [VALUE] but the
    # user may write any of:
    #   naturo set e47 "hello"            → target=e47, value=hello
    #   naturo set --aid txtSearch "query" → target=query, value=None
    #   naturo set "hello" --aid txtSearch → target=hello, value=None
    # When --aid/--role/--name/--ref already identify the element, treat
    # the first positional as the VALUE (not as an automation ID).
    has_explicit_target = ref or automation_id or role or name
    if target:
        _is_ref = (
            len(target) >= 2
            and target[0] in "emaj"
            and target[1:].isdigit()
        )
        if _is_ref:
            if not ref:
                ref = target
        elif has_explicit_target:
            # Element already identified — positional is the value
            if value is None:
                value = target
        else:
            # No explicit target — treat as automation ID
            automation_id = target

    # Validate: need a target element
    if not ref and not automation_id and not role and not name:
        emit_error(
            "INVALID_INPUT",
            "Specify a target: element ref (e47), --automation-id, "
            "or --role/--name",
            json_output,
            suggested_action="Provide a target element using a ref (e47), "
            "--automation-id, or --role/--name. Run 'naturo see' to inspect "
            "available elements.",
        )

    # Validate: need an action
    action_flags = sum([toggle, select, expand, collapse])
    if action_flags > 1:
        emit_error(
            "INVALID_INPUT",
            "Only one of --toggle, --select, --expand, --collapse "
            "can be used at a time",
            json_output,
        )

    if action_flags == 0 and value is None:
        emit_error(
            "INVALID_INPUT",
            "Specify a value to set, or use --toggle/--select/"
            "--expand/--collapse",
            json_output,
            suggested_action="Example: naturo set e47 \"hello\" or "
            "naturo set e12 --toggle",
        )

    if platform.system() not in ("Windows",) and not _has_peekaboo():
        emit_error(
            "PLATFORM_ERROR",
            "naturo set requires Windows (UIA patterns) or macOS (Peekaboo)",
            json_output,
        )

    try:
        backend = _get_backend()

        # Resolve ref to identifiers
        resolved_aid, resolved_role, resolved_name = (
            _resolve_element_identifiers(ref, automation_id, role, name)
        )

        # Resolve app/window to HWND
        target_hwnd = hwnd or 0
        if (app or window_title) and not target_hwnd:
            target_hwnd = _resolve_hwnd(backend, app, window_title)

        if toggle:
            _do_toggle(backend, target_hwnd, resolved_aid, resolved_role,
                       resolved_name, ref, json_output)
        elif select:
            _do_select(backend, target_hwnd, resolved_aid, resolved_role,
                       resolved_name, ref, json_output)
        elif expand:
            _do_expand_collapse(backend, target_hwnd, resolved_aid,
                                resolved_role, resolved_name, ref,
                                json_output, expanding=True)
        elif collapse:
            _do_expand_collapse(backend, target_hwnd, resolved_aid,
                                resolved_role, resolved_name, ref,
                                json_output, expanding=False)
        else:
            _do_set_value(backend, target_hwnd, resolved_aid, resolved_role,
                          resolved_name, ref, value, json_output)

    except NaturoError as exc:
        emit_exception_error(exc, json_output)
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="UNKNOWN_ERROR")


def _resolve_hwnd(backend, app, window_title):
    """Resolve an explicitly-supplied app/window_title selector to a handle.

    Called only when ``app`` or ``window_title`` was provided, so an unmatched
    selector is an error, not a cue to fall back to the foreground window:
    ``backend._resolve_hwnd`` raises :class:`~naturo.errors.WindowNotFoundError`
    on no match and the exception propagates to the command's error handler,
    which emits a ``WINDOW_NOT_FOUND`` envelope. Swallowing it and returning
    ``0`` (foreground) was the silent-failure bug #964 — for ``set`` it wrote
    the value to whatever window happened to be focused. Mirrors the MCP #957
    ``require_hwnd`` loud-failure contract.

    Args:
        backend: Backend instance.
        app: Application name (partial match), or ``None``.
        window_title: Window title pattern (partial match), or ``None``.

    Returns:
        The resolved window handle (int).

    Raises:
        WindowNotFoundError: When the supplied selector matches no window.
    """
    return backend._resolve_hwnd(app=app, window_title=window_title)


def _do_set_value(backend, hwnd, automation_id, role, name, ref, value,
                  json_output) -> None:
    """Set text value via UIA ValuePattern.

    Args:
        backend: Backend instance.
        hwnd: Window handle.
        automation_id: UIA AutomationId.
        role: Element role.
        name: Element name.
        ref: Original ref string (for display).
        value: Text value to set.
        json_output: Whether to output JSON.
    """
    success = backend.set_element_value(
        text=value,
        hwnd=hwnd,
        name=name,
        automation_id=automation_id,
        role=role,
    )

    if not success:
        msg = "Failed to set value"
        if ref:
            msg += f" on {ref}"
        emit_error(
            "SET_VALUE_FAILED",
            msg,
            json_output,
            suggested_action="The element may not support ValuePattern, "
            "or the value may be read-only. Try 'naturo get' to check "
            "the element's current pattern.",
        )

    if json_output:
        click.echo(json_module.dumps({
            "status": "ok",
            "action": "set_value",
            "ref": ref,
            "value": value,
            "pattern": "ValuePattern",
        }))
    else:
        target_str = ref or automation_id or f"{role}/{name}"
        click.echo(f"Set value on {target_str}: {value!r}")


def _do_toggle(backend, hwnd, automation_id, role, name, ref, json_output) -> None:
    """Toggle element via UIA TogglePattern.

    Args:
        backend: Backend instance.
        hwnd: Window handle.
        automation_id: UIA AutomationId.
        role: Element role.
        name: Element name.
        ref: Original ref string (for display).
        json_output: Whether to output JSON.
    """
    result = backend.toggle_element(
        hwnd=hwnd,
        automation_id=automation_id,
        role=role,
        name=name,
    )

    if result is None:
        msg = "Failed to toggle element"
        if ref:
            msg += f" {ref}"
        emit_error(
            "TOGGLE_FAILED",
            msg,
            json_output,
            suggested_action="The element may not support TogglePattern. "
            "Check that the target is a checkbox or toggle button.",
        )

    if json_output:
        click.echo(json_module.dumps({
            "status": "ok",
            "action": "toggle",
            "ref": ref,
            "new_state": result,
            "pattern": "TogglePattern",
        }))
    else:
        target_str = ref or automation_id or f"{role}/{name}"
        click.echo(f"Toggled {target_str} → {result}")


def _do_select(backend, hwnd, automation_id, role, name, ref, json_output) -> None:
    """Select element via UIA SelectionItemPattern.

    Args:
        backend: Backend instance.
        hwnd: Window handle.
        automation_id: UIA AutomationId.
        role: Element role.
        name: Element name.
        ref: Original ref string (for display).
        json_output: Whether to output JSON.
    """
    success = backend.select_element(
        hwnd=hwnd,
        automation_id=automation_id,
        role=role,
        name=name,
    )

    if not success:
        msg = "Failed to select element"
        if ref:
            msg += f" {ref}"
        emit_error(
            "SELECT_FAILED",
            msg,
            json_output,
            suggested_action="The element may not support "
            "SelectionItemPattern. Check that the target is a list item, "
            "radio button, or tab.",
        )

    if json_output:
        click.echo(json_module.dumps({
            "status": "ok",
            "action": "select",
            "ref": ref,
            "pattern": "SelectionItemPattern",
        }))
    else:
        target_str = ref or automation_id or f"{role}/{name}"
        click.echo(f"Selected {target_str}")


def _do_expand_collapse(backend, hwnd, automation_id, role, name, ref,
                        json_output, expanding) -> None:
    """Expand or collapse element via UIA ExpandCollapsePattern.

    Args:
        backend: Backend instance.
        hwnd: Window handle.
        automation_id: UIA AutomationId.
        role: Element role.
        name: Element name.
        ref: Original ref string (for display).
        json_output: Whether to output JSON.
        expanding: True to expand, False to collapse.
    """
    action = "expand" if expanding else "collapse"
    success = backend.expand_collapse_element(
        hwnd=hwnd,
        automation_id=automation_id,
        role=role,
        name=name,
        expand=expanding,
    )

    if not success:
        msg = f"Failed to {action} element"
        if ref:
            msg += f" {ref}"
        emit_error(
            f"{action.upper()}_FAILED",
            msg,
            json_output,
            suggested_action="The element may not support "
            "ExpandCollapsePattern. Check that the target is a combo box "
            "or tree item.",
        )

    if json_output:
        click.echo(json_module.dumps({
            "status": "ok",
            "action": action,
            "ref": ref,
            "pattern": "ExpandCollapsePattern",
        }))
    else:
        target_str = ref or automation_id or f"{role}/{name}"
        verb = "Expanded" if expanding else "Collapsed"
        click.echo(f"{verb} {target_str}")


def _has_peekaboo() -> bool:
    """Check if Peekaboo CLI is available on macOS."""
    import shutil
    return shutil.which("peekaboo") is not None
