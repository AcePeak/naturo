"""Mouse commands — scroll, drag, move."""
from __future__ import annotations

import logging

import click

import naturo.cli.interaction._common as _common

logger = logging.getLogger(__name__)


# ── scroll ───────────────────────────────────────────────────────────────────


@click.command()
@click.argument("direction_arg", required=False, default=None,
                type=click.Choice(["up", "down", "left", "right"]))
@click.option(
    "--direction", "-d",
    "direction_option",
    type=click.Choice(["up", "down", "left", "right"]),
    default=None,
    help="Scroll direction",
)
@click.option("--amount", "-a", type=int, default=3, help="Scroll amount (notches)", show_default=True)
@click.option("--on", "on_text", help="Element text or eN ref to scroll on")
@click.option("--ref", "ref_alias", hidden=True, help="Deprecated alias for --on")
@click.option("--id", "element_id", help="Element ID to scroll on")
@click.option("--coords", nargs=2, type=int, metavar="X Y", help="Coordinates to scroll at")
@click.option("--smooth", is_flag=True, help="Smooth scrolling (planned)")
@click.option("--delay", type=float, help="Delay between scroll steps (ms)")
@click.option("--app", help="Target application (name or partial match)")
@click.option("--pid", type=int, help="Process ID")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@_common._selector_option
@_common._method_option
@_common._app_id_option
@_common._see_options
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def scroll(direction_arg, direction_option, amount, on_text, ref_alias, element_id, coords,
           smooth, delay, app, pid, window_title, hwnd, selector, method, app_id, see_after, settle,
           json_output):
    """Scroll in a direction.

    DIRECTION can be: up, down, left, right (default: down)

    \b
    Examples:
      naturo scroll down
      naturo scroll up --amount 5
      naturo scroll --on e3 down --amount 5
      naturo scroll --coords 500 300 down
      naturo scroll --selector 'app://*/List[@name="Items"]' down
    """
    # --ref is a hidden deprecated alias for --on (#381)
    if ref_alias and not on_text:
        on_text = ref_alias

    # (#593) Resolve --app-id to app/hwnd/pid before any other logic
    app, hwnd, pid = _common._resolve_app_id(app_id, app, hwnd, pid, json_output)
    if app_id and hwnd is None:
        return  # Error already emitted by _resolve_app_id

    direction = direction_arg or direction_option or "down"
    if amount < 1:
        _common._json_err(f"--amount must be >= 1, got {amount}", json_output, code="INVALID_INPUT")
        return

    backend = _common._get_backend(json_output)

    # Auto-routing: detect best interaction method for target app
    route_info = _common._auto_route(app, None, method, json_output)

    # Resolve target coordinates: --selector > --coords > --on/--id
    x, y = None, None
    target_label = None

    if selector:
        resolved = _common._resolve_selector_target(
            selector, backend, app, window_title, hwnd, pid, json_output,
        )
        if resolved is None:
            return
        x, y = resolved
        target_label = selector
    elif coords:
        x, y = coords
        target_label = f"({x}, {y})"
    elif on_text or element_id:
        target_id = on_text or element_id
        import re as _re
        if _re.fullmatch(r"e\d+", target_id):
            # Resolve eN ref from most recent `see` snapshot
            from naturo.snapshot import get_snapshot_manager
            mgr = get_snapshot_manager()
            resolved = mgr.resolve_ref(target_id)
            if resolved:
                x, y = resolved[0], resolved[1]
                target_label = target_id
            else:
                _common._json_err(
                    f"Element ref '{target_id}' not found. Run 'naturo see' first to "
                    f"capture a fresh snapshot, then use the eN ref within 10 minutes.",
                    json_output,
                    code="REF_NOT_FOUND",
                )
                return
        else:
            # Text-based element lookup — find element center via backend
            try:
                elem = backend.find_element(target_id)
                if elem:
                    x = elem.x + elem.width // 2
                    y = elem.y + elem.height // 2
                    target_label = target_id
                else:
                    _common._json_err(
                        f"Element '{target_id}' not found.",
                        json_output,
                        code="ELEMENT_NOT_FOUND",
                    )
                    return
            except Exception as exc:
                _common._json_err(
                    f"Failed to find element '{target_id}': {exc}",
                    json_output,
                    code="ELEMENT_NOT_FOUND",
                )
                return

    try:
        backend.scroll(direction=direction, amount=amount, x=x, y=y, smooth=smooth)
    except Exception as exc:
        _common._json_err(str(exc), json_output)
        return

    # Record the action
    _common._record_action("scroll", {"direction": direction, "amount": amount, "x": x, "y": y})

    result_data = {"action": "scrolled", "direction": direction, "amount": amount}
    if target_label:
        result_data["target"] = target_label
    if route_info:
        result_data["routing"] = route_info

    # --see: re-capture UI tree after action
    if see_after:
        snapshot_data = _common._post_action_see(
            backend=backend, settle_ms=settle,
            app=app, window_title=window_title, hwnd=hwnd,
            json_output=json_output,
        )
        if snapshot_data and json_output:
            result_data["snapshot"] = snapshot_data

    _common._json_ok(result_data, json_output)


# ── drag ─────────────────────────────────────────────────────────────────────


@click.command()
@click.option("--from", "from_text", help="Source element text")
@click.option("--from-coords", nargs=2, type=int, metavar="X Y", help="Source X Y coordinates")
@click.option(
    "--from-selector",
    default=None,
    help=(
        "Unified selector for source element. "
        'URI format: app://notepad.exe/Button[@name="Save"]. '
        'XML format: <selector app="notepad.exe"><node role="Button" name="Save"/></selector>.'
    ),
)
@click.option("--to", "to_text", help="Destination element text")
@click.option("--to-coords", nargs=2, type=int, metavar="X Y", help="Destination X Y coordinates")
@click.option(
    "--to-selector",
    default=None,
    help=(
        "Unified selector for destination element. "
        'URI format: app://notepad.exe/ListItem[@name="Folder"]. '
        'XML format: <selector app="notepad.exe"><node role="ListItem" name="Folder"/></selector>.'
    ),
)
@click.option("--duration", type=float, default=0.5, help="Drag duration (seconds)", show_default=True)
@click.option("--steps", type=int, default=10, help="Interpolation steps", show_default=True)
@click.option("--modifiers", multiple=True, help="Modifier keys to hold (ctrl, shift, alt)")
@click.option(
    "--profile",
    type=click.Choice(["linear", "ease-in-out"]),
    default="linear",
    help="Motion profile",
)
@click.option("--app", help="Target application (name or partial match)")
@click.option("--pid", type=int, help="Process ID")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@_common._method_option
@_common._app_id_option
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def drag(from_text, from_coords, from_selector, to_text, to_coords, to_selector,
         duration, steps, modifiers, profile, app, pid, window_title, hwnd, method,
         app_id, json_output):
    """Drag from one element/position to another.

    \b
    Examples:
      naturo drag --from e5 --to e12
      naturo drag --from-coords 100 100 --to-coords 500 300
      naturo drag --from e5 --to-coords 500 300
      naturo drag --from-selector 'app://*/ListItem[@name="File1"]' --to-selector 'app://*/TreeItem[@name="Folder"]'
    """
    # (#593) Resolve --app-id to app/hwnd/pid before any other logic
    app, hwnd, pid = _common._resolve_app_id(app_id, app, hwnd, pid, json_output)
    if app_id and hwnd is None:
        return  # Error already emitted by _resolve_app_id

    # Resolve element refs (eN) from snapshot for --from and --to (#154)
    import re as _re
    from naturo.snapshot import get_snapshot_manager

    backend = _common._get_backend(json_output)

    fx, fy = None, None
    tx, ty = None, None
    from_label = None
    to_label = None

    # Resolve source: --from-selector > --from-coords > --from (eN ref)
    if from_selector:
        resolved = _common._resolve_selector_target(
            from_selector, backend, app, window_title, hwnd, pid, json_output,
        )
        if resolved is None:
            return
        fx, fy = resolved
        from_label = from_selector
    elif from_coords:
        fx, fy = from_coords
    elif from_text and _re.fullmatch(r"e\d+", from_text):
        mgr = get_snapshot_manager()
        resolved = mgr.resolve_ref(from_text)
        if resolved:
            fx, fy = resolved[0], resolved[1]
            from_label = from_text
        else:
            _common._json_err(
                f"Source element ref '{from_text}' not found or has zero-size bounds. "
                f"Run 'naturo see' first to capture a fresh snapshot.",
                json_output,
                code="REF_NOT_FOUND",
            )
            return
    else:
        _common._json_err(
            "Specify source: --from-selector, --from-coords X Y, or --from eN "
            "(element ref from 'naturo see')",
            json_output,
            code="INVALID_INPUT",
        )
        return

    # Resolve destination: --to-selector > --to-coords > --to (eN ref)
    if to_selector:
        resolved = _common._resolve_selector_target(
            to_selector, backend, app, window_title, hwnd, pid, json_output,
        )
        if resolved is None:
            return
        tx, ty = resolved
        to_label = to_selector
    elif to_coords:
        tx, ty = to_coords
    elif to_text and _re.fullmatch(r"e\d+", to_text):
        mgr = get_snapshot_manager()
        resolved = mgr.resolve_ref(to_text)
        if resolved:
            tx, ty = resolved[0], resolved[1]
            to_label = to_text
        else:
            _common._json_err(
                f"Destination element ref '{to_text}' not found or has zero-size bounds. "
                f"Run 'naturo see' first to capture a fresh snapshot.",
                json_output,
                code="REF_NOT_FOUND",
            )
            return
    else:
        _common._json_err(
            "Specify destination: --to-selector, --to-coords X Y, or --to eN "
            "(element ref from 'naturo see')",
            json_output,
            code="INVALID_INPUT",
        )
        return

    if steps < 1:
        _common._json_err(f"--steps must be >= 1, got {steps}", json_output, code="INVALID_INPUT")
        return
    if duration < 0:
        _common._json_err(f"--duration must be >= 0, got {duration}", json_output, code="INVALID_INPUT")
        return

    duration_ms = int(duration * 1000)

    try:
        backend.drag(from_x=fx, from_y=fy, to_x=tx, to_y=ty,
                     duration_ms=duration_ms, steps=steps)
    except Exception as exc:
        _common._json_err(str(exc), json_output)
        return

    # Record the action
    _common._record_action("drag", {
        "from_x": fx, "from_y": fy, "to_x": tx, "to_y": ty,
        "steps": steps, "duration": duration,
    })

    result = {
        "action": "dragged",
        "from": [fx, fy],
        "to": [tx, ty],
        "duration_ms": duration_ms,
    }
    if from_label:
        result["from_ref"] = from_label
    if to_label:
        result["to_ref"] = to_label
    _common._json_ok(result, json_output)


# ── move ─────────────────────────────────────────────────────────────────────


@click.command()
@click.option("--to", "to_text", help="Target element text")
@click.option("--coords", nargs=2, type=int, metavar="X Y", help="Target X Y coordinates")
@click.option("--id", "element_id", help="Target element automation ID")
@click.option("--duration", type=float, default=0.0, help="Move duration (seconds)", hidden=True)
@click.option("--app", help="Target application (name or partial match)")
@click.option("--pid", type=int, help="Process ID")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@_common._selector_option
@_common._method_option
@_common._app_id_option
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def move(to_text, coords, element_id, duration, app, pid, window_title, hwnd,
         selector, method, app_id, json_output):
    """Move the mouse cursor to a target element or coordinates.

    \b
    Examples:
      naturo move --coords 500 300
      naturo move --selector 'app://*/Button[@name="Save"]'
    """
    # (#593) Resolve --app-id to app/hwnd/pid before any other logic
    app, hwnd, pid = _common._resolve_app_id(app_id, app, hwnd, pid, json_output)
    if app_id and hwnd is None:
        return  # Error already emitted by _resolve_app_id

    backend = _common._get_backend(json_output)

    # Resolve target: --selector > --coords
    x, y = None, None

    if selector:
        resolved = _common._resolve_selector_target(
            selector, backend, app, window_title, hwnd, pid, json_output,
        )
        if resolved is None:
            return
        x, y = resolved
    elif coords:
        x, y = coords
    else:
        _common._json_err("Specify --selector, --coords X Y, or --to", json_output, code="INVALID_INPUT")
        return

    try:
        backend.move_mouse(x, y)
    except Exception as exc:
        _common._json_err(str(exc), json_output)
        return

    # Record the action
    _common._record_action("move", {"x": x, "y": y})

    _common._json_ok({"action": "moved", "x": x, "y": y}, json_output)
