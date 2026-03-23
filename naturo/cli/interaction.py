"""Interaction commands: click, type, press, hotkey, scroll, drag, move."""
from __future__ import annotations

import json
import logging
import platform
import sys
import time as _time

import click

logger = logging.getLogger(__name__)


# ── --see flag (post-action UI snapshot) ─────────────────────────────────────


def _see_options(func):
    """Shared Click decorator that adds --see and --settle to action commands.

    When ``--see`` is passed, the command re-captures the UI element tree
    after the action completes (with a configurable settle delay) and
    appends the snapshot to the output.
    """
    func = click.option(
        "--settle",
        type=int,
        default=300,
        help="Wait time in ms before re-snapshot (used with --see)",
        show_default=True,
    )(func)
    func = click.option(
        "--see",
        "see_after",
        is_flag=True,
        help="Capture and display updated UI tree after action",
    )(func)
    return func


def _post_action_see(
    backend,
    settle_ms: int,
    app: str | None,
    window_title: str | None,
    hwnd: int | None,
    json_output: bool,
    depth: int = 3,
) -> dict | None:
    """Run UI inspection after an interaction and return snapshot data.

    Args:
        backend: The platform backend instance.
        settle_ms: Milliseconds to wait for UI to settle before capture.
        app: Application name filter (passed to get_element_tree).
        window_title: Window title filter.
        hwnd: Window handle filter.
        json_output: Whether JSON output mode is active.
        depth: Maximum tree depth for element inspection.

    Returns:
        A dict with snapshot data (for JSON embedding) or None on failure.
        In text mode, also prints the tree to stdout.
    """
    import time
    if settle_ms > 0:
        time.sleep(settle_ms / 1000.0)

    try:
        tree = backend.get_element_tree(
            app=app, window_title=window_title, hwnd=hwnd, depth=depth,
            backend="uia",
        )
    except Exception as exc:
        logger.debug("--see: failed to capture UI tree: %s", exc)
        if not json_output:
            click.echo(f"\n--- UI snapshot (failed) ---\nError: {exc}", err=True)
        return None

    if tree is None:
        if not json_output:
            click.echo("\n--- UI snapshot (empty) ---\nNo window found or UI tree is empty.")
        return None

    # Store snapshot with ref mapping
    from naturo.snapshot import SnapshotManager
    from naturo.models.snapshot import UIElement

    mgr = SnapshotManager()
    snapshot_id = mgr.create_snapshot()

    ui_map = {}
    _ref_seq = [0]
    ref_map = {}

    def _flatten(el, parent_id=None):
        _ref_seq[0] += 1
        ref = f"e{_ref_seq[0]}"
        child_ids = [c.id for c in el.children]
        props = getattr(el, "properties", {})
        ui_map[el.id] = UIElement(
            id=el.id,
            element_id=f"element_{el.id}",
            role=el.role,
            title=el.name,
            label=el.name,
            value=el.value,
            frame=(el.x, el.y, el.width, el.height),
            is_actionable=getattr(el, "is_actionable", False),
            parent_id=props.get("parent_id", parent_id),
            children=child_ids,
            keyboard_shortcut=props.get("keyboard_shortcut"),
        )
        ref_map[ref] = el.id
        for child in el.children:
            _flatten(child, parent_id=el.id)

    _flatten(tree)
    mgr.store_detection_result(snapshot_id, ui_map)
    mgr.store_ref_map(snapshot_id, ref_map)

    if json_output:
        # Build JSON-serializable tree
        def _to_dict(el):
            d = {
                "id": el.id,
                "role": el.role,
                "name": el.name,
                "value": el.value,
                "x": el.x,
                "y": el.y,
                "width": el.width,
                "height": el.height,
                "children": [_to_dict(c) for c in el.children],
            }
            # Flag zero-bounds elements (#137) so callers can detect stale refs
            if el.width == 0 and el.height == 0:
                d["zero_bounds"] = True
            return d

        return {"id": snapshot_id, "elements": _to_dict(tree)}
    else:
        # Print tree with refs
        _ref_counter = [0]

        def _print_tree(el, indent=0):
            _ref_counter[0] += 1
            ref = f"e{_ref_counter[0]}"
            prefix = "  " * indent
            name_str = f' "{el.name}"' if el.name else ""
            pos_str = f" ({el.x},{el.y} {el.width}x{el.height})"
            # Warn about zero-bounds elements (#137) — these are likely stale
            # after window state changes and won't respond to coordinate clicks.
            zero_warn = " ⚠️ zero-bounds" if el.width == 0 and el.height == 0 else ""
            click.echo(f"{prefix}[{el.role}]{name_str}{pos_str} {ref}{zero_warn}")
            for child in el.children:
                _print_tree(child, indent + 1)

        click.echo(f"\n--- UI snapshot (updated) ---")
        _print_tree(tree)
        click.echo(f"Snapshot: {snapshot_id}")
        return {"id": snapshot_id}


def _record_action(command: str, args: dict, duration_ms: float = 0.0) -> None:
    """No-op stub — recording command removed."""
    pass


# ── Method override ──────────────────────────────────────────────────────────

# Valid interaction methods for --method flag.
# "auto" = let the system pick (default); others force a specific channel.
VALID_METHODS = ("auto", "cdp", "uia", "msaa", "ia2", "jab", "vision")


def _method_option(func):
    """Shared Click decorator that adds --method to an action command.

    The flag lets users bypass auto-detection and force a specific
    interaction channel.  When set to anything other than "auto",
    auto-routing (#28) is skipped and the specified method is used
    directly (if available for the target application).
    """
    return click.option(
        "--method", "-m",
        type=click.Choice(VALID_METHODS),
        default="auto",
        help=(
            "Interaction method override: auto (default), cdp, uia, msaa, "
            "ia2, jab, vision. Bypasses auto-detection when set explicitly."
        ),
        show_default=True,
    )(func)


def _validate_method(method: str, json_output: bool) -> bool:
    """Validate the --method flag value.

    Returns True if valid, otherwise emits an error and returns False.
    Currently always returns True because Click.Choice already validates,
    but kept as a hook for future runtime availability checks.
    """
    return True

# ── Shared helper ────────────────────────────────────────────────────────────


def _check_desktop_session() -> None:
    """Raise NoDesktopSessionError if running without an interactive desktop.

    On Windows, verifies the *current* session has desktop access — not just
    that a desktop exists somewhere on the machine.

    Detection logic:
    1. SESSIONNAME == "Console" or starts with "RDP-Tcp" → interactive desktop, OK.
    2. SESSIONNAME == "Services" or empty/unset → likely non-interactive.
       - If empty AND explorer.exe is running, this is the SSH-into-desktop-machine
         scenario: another session owns the desktop but *this* session cannot
         interact with it. Raise a clear error instead of letting COM fail.
    3. Any other SESSIONNAME value → assume interactive (e.g., Citrix, VNC).

    No-op on other platforms.
    """
    import platform as _plat
    if _plat.system() != "Windows":
        return

    import os
    session = os.environ.get("SESSIONNAME", "")
    session_lower = session.lower()

    # Known interactive session types — allow through
    if session_lower == "console" or session_lower.startswith("rdp-tcp"):
        return

    # Known non-interactive session types — reject
    if session_lower == "services":
        from naturo.errors import NoDesktopSessionError
        raise NoDesktopSessionError()

    # Empty/unset SESSIONNAME — SSH or headless service
    if not session:
        # Even if explorer.exe is running (from an RDP/Console session),
        # this SSH session cannot interact with that desktop.
        # Provide a specific error message for this scenario.
        import subprocess
        explorer_running = False
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq explorer.exe", "/NH", "/FO", "CSV"],
                capture_output=True, text=True, timeout=5,
                encoding="utf-8", errors="replace",
            )
            explorer_running = "explorer.exe" in result.stdout.lower()
        except Exception:
            pass

        from naturo.errors import NoDesktopSessionError
        if explorer_running:
            raise NoDesktopSessionError(
                "No interactive desktop in this session. "
                "A desktop session exists on this machine (explorer.exe running), "
                "but the current SSH/service session cannot interact with it. "
                "Connect via RDP or Console instead."
            )
        raise NoDesktopSessionError()

    # Any other SESSIONNAME value (Citrix ICA, VNC, etc.) — assume interactive
    return


def _get_backend(json_output: bool = False):
    """Return the platform backend, raising UsageError if unavailable.

    Also performs a pre-flight check for an interactive desktop session
    on Windows to provide clear errors instead of cryptic COM exceptions.

    Args:
        json_output: When True, emit JSON-formatted error and sys.exit
            instead of raising an exception for NoDesktopSessionError.
    """
    try:
        _check_desktop_session()
    except Exception as exc:
        if json_output:
            from naturo.cli.error_helpers import json_error
            click.echo(json_error("NO_DESKTOP_SESSION", str(exc)))
            sys.exit(1)
        raise click.UsageError(str(exc))
    from naturo.backends.base import get_backend
    try:
        return get_backend()
    except Exception as exc:
        if json_output:
            _json_err(str(exc), True, code="BACKEND_ERROR")
        raise click.UsageError(str(exc))


def _json_ok(data: dict, json_output: bool) -> None:
    """Emit success result as JSON or plain text."""
    if json_output:
        click.echo(json.dumps({"success": True, "data": data}))
    else:
        for k, v in data.items():
            click.echo(f"{k}: {v}")


def _json_err(msg: str, json_output: bool, exit_code: int = 1,
              code: str = "ACTION_ERROR") -> None:
    """Emit error result as JSON or plain text, then exit.

    Includes agent-friendly recovery hints from the error_helpers registry.
    """
    if json_output:
        from naturo.cli.error_helpers import json_error
        click.echo(json_error(code, msg))
    else:
        click.echo(f"Error: {msg}", err=True)
    sys.exit(exit_code)


# ── Auto-routing helper ──────────────────────────────────────────────────────


def _auto_route(
    app: str | None,
    pid: int | None,
    method: str,
    json_output: bool,
) -> dict:
    """Run auto-routing and return routing metadata for output.

    When --method is "auto" and an --app or --pid is specified, runs the
    detection chain to determine the best interaction method. Returns a
    dict with routing info to include in JSON output.

    Args:
        app: Application name from --app flag.
        pid: Process ID from --pid flag.
        method: Value of --method flag ("auto" or explicit method).
        json_output: Whether JSON output mode is active.

    Returns:
        Dict with routing info (method, source, framework, etc.).
        Empty dict if no routing was performed.
    """
    if method == "auto" and (app is not None or pid is not None):
        try:
            from naturo.routing import resolve_method

            result = resolve_method(app=app, pid=pid, explicit_method=method)
            route_info = result.to_dict()
            if not json_output:
                src = f" ({result.framework})" if result.framework != "unknown" else ""
                logger.info(
                    "Auto-routed: %s → %s%s",
                    app or f"PID {pid}",
                    result.method,
                    src,
                )
            return route_info
        except Exception as exc:
            logger.debug("Auto-routing failed: %s", exc)
    return {}


# ── click ────────────────────────────────────────────────────────────────────


@click.command("click")
@click.argument("query", required=False)
@click.option("--on", "on_text", help="Target element (eN ref or text label)")
@click.option("--id", "element_id", help="Automation element ID")
@click.option("--coords", nargs=2, type=int, metavar="X Y", help="X Y coordinates")
@click.option("--double", is_flag=True, help="Double-click")
@click.option("--right", is_flag=True, help="Right-click")
@click.option("--app", help="Target application (name or partial match)")
@click.option("--pid", type=int, help="Process ID")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option("--window-id", "hwnd", type=int, default=None, hidden=True, help="")
@click.option("--wait-for", type=float, help="Wait for element (seconds)", hidden=True)
@click.option(
    "--input-mode",
    type=click.Choice(["normal", "hardware", "hook"]),
    default="normal",
    help="Input method: normal (SendInput), hardware (Phys32 driver), hook (MinHook injection)",
)
@_method_option
@_see_options
@click.option("--process-name", "app", default=None, hidden=True, help="")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def click_cmd(query, on_text, element_id, coords, double, right, app, pid,
              window_title, hwnd, wait_for, input_mode, method,
              see_after, settle, json_output):
    """Click on a UI element, text, or coordinates.

    QUERY is optional text to find and click on. Use --on, --id, or --coords
    for alternative targeting.

    Input modes (Windows-specific):
      normal   — SendInput API (default, works for most apps)
      hardware — Phys32 driver (bypasses software input filtering)
      hook     — MinHook injection (for protected/game apps)

    \b
    Examples:
      naturo click --coords 500 300
      naturo click --coords 500 300 --right
      naturo click --id "button_ok"
    """
    backend = _get_backend(json_output)

    # Auto-routing: detect best interaction method for target app
    route_info = _auto_route(app, pid, method, json_output)

    button = "right" if right else "left"

    # Resolve target coordinates or element_id
    if coords:
        x, y = coords
        target_id = None
    elif element_id:
        x, y = None, None
        target_id = element_id
    elif on_text or query:
        # Find element by text
        selector = on_text or query
        target_id = selector
        x, y = None, None
    else:
        _json_err("Specify --coords X Y, --id, or --on TEXT", json_output, code="INVALID_INPUT")
        return

    # BUG-074: Resolve eN refs from the most recent `see` snapshot
    import re as _re
    _zero_bounds_element = None  # Track element for Invoke fallback (#137)
    if target_id and _re.fullmatch(r"e\d+", target_id):
        from naturo.snapshot import SnapshotManager
        mgr = SnapshotManager()
        resolved = mgr.resolve_ref(target_id)
        if resolved:
            x, y = resolved[0], resolved[1]
            target_id = None  # use coordinates instead
        else:
            # resolve_ref returns None for both "not found" and "zero-bounds".
            # Check resolve_ref_element to distinguish: if the element exists
            # but has zero-bounds, try UIA Invoke pattern (#137/#135).
            el_result = mgr.resolve_ref_element(target_id)
            if el_result is not None:
                element, _snap_id = el_result
                ex, ey, ew, eh = element.frame
                if ew == 0 and eh == 0:
                    _zero_bounds_element = element
                    target_id = None  # Will use Invoke fallback below
                else:
                    # Element found with valid bounds — shouldn't happen, but
                    # fall through to coordinate click just in case.
                    x, y = ex + ew // 2, ey + eh // 2
                    target_id = None
            else:
                _json_err(
                    f"Element ref '{target_id}' not found. Run 'naturo see' first to "
                    f"capture a fresh snapshot, then use the eN ref within 10 minutes.",
                    json_output,
                    code="REF_NOT_FOUND",
                )
                return

    try:
        if _zero_bounds_element is not None:
            # Zero-bounds fallback (#137): attempt UIA Invoke pattern for
            # elements whose bounding rects are (0,0 0x0) after window
            # state changes.
            _invoked = False
            if hasattr(backend, "invoke_element"):
                _invoked = backend.invoke_element(
                    name=_zero_bounds_element.title or "",
                    role=_zero_bounds_element.role,
                )
            if not _invoked:
                _json_err(
                    f"Element has zero-size bounds (0,0 0x0) — likely stale after "
                    f"a window state change. UIA Invoke fallback {'not available' if not hasattr(backend, 'invoke_element') else 'failed'}. "
                    f"Try running 'naturo see' again to refresh the snapshot.",
                    json_output,
                    code="ZERO_BOUNDS",
                )
                return
        elif target_id:
            backend.click(element_id=target_id, button=button, double=double,
                          input_mode=input_mode)
        else:
            backend.click(x=x, y=y, button=button, double=double,
                          input_mode=input_mode)
    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    # Record the action
    _record_action("click", {
        "x": x, "y": y, "button": button, "double_click": double,
    })

    action = "double-clicked" if double else "clicked"
    if _zero_bounds_element is not None:
        loc = f"{_zero_bounds_element.title or _zero_bounds_element.role} (via UIA Invoke)"
    else:
        loc = f"({x}, {y})" if coords else (target_id or "element")
    result_data = {"action": action, "target": str(loc), "button": button}
    if route_info:
        result_data["routing"] = route_info

    # --see: re-capture UI tree after action
    if see_after:
        snapshot_data = _post_action_see(
            backend=backend, settle_ms=settle,
            app=app, window_title=window_title, hwnd=hwnd,
            json_output=json_output,
        )
        if snapshot_data and json_output:
            result_data["snapshot"] = snapshot_data

    _json_ok(result_data, json_output)


# ── type ─────────────────────────────────────────────────────────────────────


@click.command("type")
@click.argument("text", required=False)
@click.option("--delay", type=float, default=5.0, help="Delay between keystrokes (ms)", show_default=True)
@click.option(
    "--profile",
    type=click.Choice(["human", "linear"]),
    default="linear",
    help="Typing profile: human (variable delay), linear (constant delay)",
    show_default=True,
)
@click.option("--wpm", type=int, default=120, help="Words per minute (for human profile)", show_default=True)
@click.option("--return", "press_return", is_flag=True, help="Press Return after typing")
@click.option("--tab", "tab_count", type=int, help="Press Tab N times after typing")
@click.option("--escape", is_flag=True, help="Press Escape after typing")
@click.option("--delete", is_flag=True, help="Delete existing text first")
@click.option("--clear", is_flag=True, help="Select all + delete before typing")
@click.option("--paste", "paste_mode", is_flag=True, help="Paste via clipboard (Ctrl+V) instead of typing")
@click.option("--file", "file_path", type=click.Path(), help="Read text from file (use with --paste)")
@click.option("--restore/--no-restore", default=True, help="Restore clipboard after --paste", show_default=True)
@click.option("--app", help="Target application (name or partial match)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option(
    "--input-mode",
    type=click.Choice(["normal", "hardware", "hook"]),
    default="normal",
    help="Input method: normal (SendInput), hardware (Phys32), hook (MinHook)",
)
@_method_option
@_see_options
@click.option("--process-name", "app", default=None, hidden=True, help="")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def type_cmd(text, delay, profile, wpm, press_return, tab_count, escape,
             delete, clear, paste_mode, file_path, restore, app, window_title,
             hwnd, input_mode, method, see_after, settle, json_output):
    """Type text with configurable speed and profile.

    TEXT is the string to type. Supports human-like variable-speed typing
    and Windows-specific input modes.

    Use --paste to set clipboard and Ctrl+V instead of keystroke typing.
    Use --file with --paste to read content from a file.

    \b
    Examples:
      naturo type "Hello World"
      naturo type "Hello" --return
      naturo type "text" --profile human --wpm 60
      naturo type "large content" --paste
      naturo type --paste --file mytext.txt
    """
    # Handle --file: read content from file
    if file_path:
        import os
        if not os.path.exists(file_path):
            _json_err(f"File not found: {file_path}", json_output, code="INVALID_INPUT")
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as exc:
            _json_err(str(exc), json_output, code="FILE_ERROR")
            return
        # --file implies --paste
        paste_mode = True

    if not text:
        _json_err("TEXT argument is required", json_output, code="INVALID_INPUT")
        return

    if wpm < 1:
        _json_err(f"--wpm must be >= 1, got {wpm}", json_output, code="INVALID_INPUT")
        return

    backend = _get_backend(json_output)

    # Auto-routing: detect best interaction method for target app
    route_info = _auto_route(app, None, method, json_output)

    try:
        if clear:
            backend.hotkey("ctrl", "a")
            backend.press_key("delete")
        elif delete:
            backend.press_key("delete")

        if paste_mode:
            # Paste via clipboard: save → set → Ctrl+V → restore
            old_clip = ""
            if restore:
                try:
                    old_clip = backend.clipboard_get()
                except Exception:
                    pass
            backend.clipboard_set(text)
            backend.hotkey("ctrl", "v")
            if restore and old_clip:
                import time
                time.sleep(0.1)
                backend.clipboard_set(old_clip)
        else:
            backend.type_text(text, delay_ms=int(delay), profile=profile, wpm=wpm,
                              input_mode=input_mode)

        if press_return:
            backend.press_key("enter")
        if tab_count:
            for _ in range(tab_count):
                backend.press_key("tab")
        if escape:
            backend.press_key("escape")

    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    action = "pasted" if paste_mode else "typed"
    result_data = {"action": action, "text": text, "length": len(text)}
    if route_info:
        result_data["routing"] = route_info

    # --see: re-capture UI tree after action
    if see_after:
        snapshot_data = _post_action_see(
            backend=backend, settle_ms=settle,
            app=app, window_title=window_title, hwnd=hwnd,
            json_output=json_output,
        )
        if snapshot_data and json_output:
            result_data["snapshot"] = snapshot_data

    _json_ok(result_data, json_output)


# ── press ────────────────────────────────────────────────────────────────────


@click.command()
@click.argument("key", required=False, default=None)
@click.option("--count", "-n", type=int, default=1, help="Number of times to press", show_default=True)
@click.option("--delay", type=float, default=50.0, help="Delay between presses (ms)", show_default=True)
@click.option("--app", help="Target application (name or partial match)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option(
    "--input-mode",
    type=click.Choice(["normal", "hardware", "hook"]),
    default="normal",
    help="Input method",
)
@_method_option
@_see_options
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def press(key, count, delay, app, window_title, hwnd, input_mode, method, see_after, settle, json_output):
    """Press a single key or key sequence.

    KEY can be a key name (enter, tab, escape, f1-f12, a-z, 0-9, etc.)

    \b
    Examples:
      naturo press enter
      naturo press tab --count 3
      naturo press f5
    """
    if key is None:
        _json_err("Missing argument 'KEY'. Provide a key name (e.g., enter, tab, f1).",
                  json_output, code="INVALID_INPUT")
        return

    if count < 1:
        _json_err(f"--count must be >= 1, got {count}", json_output, code="INVALID_INPUT")
        return

    import time
    backend = _get_backend(json_output)

    # Auto-routing: detect best interaction method for target app
    route_info = _auto_route(app, None, method, json_output)

    try:
        for i in range(count):
            backend.press_key(key, input_mode=input_mode)
            if i < count - 1 and delay > 0:
                time.sleep(delay / 1000.0)
    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    # Record the action
    _record_action("press", {"key": key, "count": count})

    result_data = {"action": "pressed", "key": key, "count": count}
    if route_info:
        result_data["routing"] = route_info

    # --see: re-capture UI tree after action
    if see_after:
        snapshot_data = _post_action_see(
            backend=backend, settle_ms=settle,
            app=app, window_title=window_title, hwnd=hwnd,
            json_output=json_output,
        )
        if snapshot_data and json_output:
            result_data["snapshot"] = snapshot_data

    _json_ok(result_data, json_output)


# ── hotkey ───────────────────────────────────────────────────────────────────


@click.command()
@click.argument("keys", required=False)
@click.option("--keys", "keys_option", multiple=True, help="Key names (repeatable)")
@click.option("--hold-duration", type=float, help="Hold duration in ms")
@click.option("--app", help="Target application (name or partial match)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@click.option(
    "--input-mode",
    type=click.Choice(["normal", "hardware", "hook"]),
    default="normal",
    help="Input method",
)
@_method_option
@_see_options
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def hotkey(keys, keys_option, hold_duration, app, window_title, hwnd,
           input_mode, method, see_after, settle, json_output):
    """Press a hotkey combination.

    KEYS as a string like "ctrl+c" or "alt+f4". Or use --keys for each key.

    \b
    Examples:
      naturo hotkey ctrl+c
      naturo hotkey ctrl+z
      naturo hotkey --keys ctrl --keys shift --keys z
    """
    # Validate parameters BEFORE acquiring backend (which may raise
    # NoDesktopSessionError on headless CI).
    # Parse key combo from positional arg (e.g. "ctrl+c") or --keys options
    if keys:
        key_list = [k.strip() for k in keys.replace("+", " ").split()]
    elif keys_option:
        key_list = list(keys_option)
    else:
        _json_err("Specify keys as 'ctrl+c' or via --keys ctrl --keys c", json_output, code="INVALID_INPUT")
        return

    if hold_duration is not None and hold_duration < 0:
        _json_err(f"--hold-duration must be >= 0, got {hold_duration}", json_output, code="INVALID_INPUT")
        return

    backend = _get_backend(json_output)

    # Auto-routing: detect best interaction method for target app
    route_info = _auto_route(app, None, method, json_output)

    try:
        backend.hotkey(*key_list,
                       hold_duration_ms=int(hold_duration) if hold_duration else 50,
                       input_mode=input_mode)
    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    # Record the action
    _record_action("hotkey", {"keys": key_list, "hold_duration": hold_duration or 0.05})

    combo = "+".join(key_list)
    result_data = {"action": "hotkey", "combo": combo}
    if route_info:
        result_data["routing"] = route_info

    # --see: re-capture UI tree after action
    if see_after:
        snapshot_data = _post_action_see(
            backend=backend, settle_ms=settle,
            app=app, window_title=window_title, hwnd=hwnd,
            json_output=json_output,
        )
        if snapshot_data and json_output:
            result_data["snapshot"] = snapshot_data

    _json_ok(result_data, json_output)


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
@click.option("--id", "element_id", help="Element ID to scroll on")
@click.option("--coords", nargs=2, type=int, metavar="X Y", help="Coordinates to scroll at")
@click.option("--smooth", is_flag=True, help="Smooth scrolling (Phase 3)")
@click.option("--delay", type=float, help="Delay between scroll steps (ms)")
@click.option("--app", help="Target application (name or partial match)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@_method_option
@_see_options
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def scroll(direction_arg, direction_option, amount, on_text, element_id, coords,
           smooth, delay, app, window_title, hwnd, method, see_after, settle, json_output):
    """Scroll in a direction.

    DIRECTION can be: up, down, left, right (default: down)

    \b
    Examples:
      naturo scroll down
      naturo scroll up --amount 5
      naturo scroll --on e3 down --amount 5
      naturo scroll --coords 500 300 down
    """
    direction = direction_arg or direction_option or "down"
    if amount < 1:
        _json_err(f"--amount must be >= 1, got {amount}", json_output, code="INVALID_INPUT")
        return

    backend = _get_backend(json_output)

    # Auto-routing: detect best interaction method for target app
    route_info = _auto_route(app, None, method, json_output)

    # Resolve target coordinates from --on, --id, or --coords
    x, y = None, None
    target_label = None

    if coords:
        x, y = coords
        target_label = f"({x}, {y})"
    elif on_text or element_id:
        target_id = on_text or element_id
        import re as _re
        if _re.fullmatch(r"e\d+", target_id):
            # Resolve eN ref from most recent `see` snapshot
            from naturo.snapshot import SnapshotManager
            mgr = SnapshotManager()
            resolved = mgr.resolve_ref(target_id)
            if resolved:
                x, y = resolved[0], resolved[1]
                target_label = target_id
            else:
                _json_err(
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
                    _json_err(
                        f"Element '{target_id}' not found.",
                        json_output,
                        code="ELEMENT_NOT_FOUND",
                    )
                    return
            except Exception as exc:
                _json_err(
                    f"Failed to find element '{target_id}': {exc}",
                    json_output,
                    code="ELEMENT_NOT_FOUND",
                )
                return

    try:
        backend.scroll(direction=direction, amount=amount, x=x, y=y, smooth=smooth)
    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    # Record the action
    _record_action("scroll", {"direction": direction, "amount": amount, "x": x, "y": y})

    result_data = {"action": "scrolled", "direction": direction, "amount": amount}
    if target_label:
        result_data["target"] = target_label
    if route_info:
        result_data["routing"] = route_info

    # --see: re-capture UI tree after action
    if see_after:
        snapshot_data = _post_action_see(
            backend=backend, settle_ms=settle,
            app=app, window_title=window_title, hwnd=hwnd,
            json_output=json_output,
        )
        if snapshot_data and json_output:
            result_data["snapshot"] = snapshot_data

    _json_ok(result_data, json_output)


# ── drag ─────────────────────────────────────────────────────────────────────


@click.command()
@click.option("--from", "from_text", help="Source element text")
@click.option("--from-coords", nargs=2, type=int, metavar="X Y", help="Source X Y coordinates")
@click.option("--to", "to_text", help="Destination element text")
@click.option("--to-coords", nargs=2, type=int, metavar="X Y", help="Destination X Y coordinates")
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
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@_method_option
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def drag(from_text, from_coords, to_text, to_coords, duration, steps,
         modifiers, profile, app, window_title, hwnd, method, json_output):
    """Drag from one element/position to another.

    \b
    Examples:
      naturo drag --from e5 --to e12
      naturo drag --from-coords 100 100 --to-coords 500 300
      naturo drag --from e5 --to-coords 500 300
    """
    # Resolve element refs (eN) from snapshot for --from and --to (#154)
    import re as _re
    from naturo.snapshot import SnapshotManager

    fx, fy = None, None
    tx, ty = None, None
    from_label = None
    to_label = None

    if from_coords:
        fx, fy = from_coords
    elif from_text and _re.fullmatch(r"e\d+", from_text):
        mgr = SnapshotManager()
        resolved = mgr.resolve_ref(from_text)
        if resolved:
            fx, fy = resolved[0], resolved[1]
            from_label = from_text
        else:
            _json_err(
                f"Source element ref '{from_text}' not found or has zero-size bounds. "
                f"Run 'naturo see' first to capture a fresh snapshot.",
                json_output,
                code="REF_NOT_FOUND",
            )
            return
    else:
        _json_err(
            "Specify source: --from-coords X Y or --from eN (element ref from 'naturo see')",
            json_output,
            code="INVALID_INPUT",
        )
        return

    if to_coords:
        tx, ty = to_coords
    elif to_text and _re.fullmatch(r"e\d+", to_text):
        mgr = SnapshotManager()
        resolved = mgr.resolve_ref(to_text)
        if resolved:
            tx, ty = resolved[0], resolved[1]
            to_label = to_text
        else:
            _json_err(
                f"Destination element ref '{to_text}' not found or has zero-size bounds. "
                f"Run 'naturo see' first to capture a fresh snapshot.",
                json_output,
                code="REF_NOT_FOUND",
            )
            return
    else:
        _json_err(
            "Specify destination: --to-coords X Y or --to eN (element ref from 'naturo see')",
            json_output,
            code="INVALID_INPUT",
        )
        return

    if steps < 1:
        _json_err(f"--steps must be >= 1, got {steps}", json_output, code="INVALID_INPUT")
        return
    if duration < 0:
        _json_err(f"--duration must be >= 0, got {duration}", json_output, code="INVALID_INPUT")
        return

    backend = _get_backend(json_output)
    duration_ms = int(duration * 1000)

    try:
        backend.drag(from_x=fx, from_y=fy, to_x=tx, to_y=ty,
                     duration_ms=duration_ms, steps=steps)
    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    # Record the action
    _record_action("drag", {
        "from_x": fx, "from_y": fy, "to_x": tx, "to_y": ty,
        "steps": steps, "duration": duration,
    })

    from_str = f"{from_label} ({fx}, {fy})" if from_label else f"({fx}, {fy})"
    to_str = f"{to_label} ({tx}, {ty})" if to_label else f"({tx}, {ty})"
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
    _json_ok(result, json_output)


# ── move ─────────────────────────────────────────────────────────────────────


@click.command()
@click.option("--to", "to_text", help="Target element text")
@click.option("--coords", nargs=2, type=int, metavar="X Y", help="Target X Y coordinates")
@click.option("--id", "element_id", help="Target element automation ID")
@click.option("--duration", type=float, default=0.0, help="Move duration (seconds)", hidden=True)
@click.option("--app", help="Target application (name or partial match)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@_method_option
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def move(to_text, coords, element_id, duration, app, window_title, hwnd,
         method, json_output):
    """Move the mouse cursor to a target element or coordinates.

    \b
    Examples:
      naturo move --coords 500 300
    """
    if not coords:
        _json_err("Specify --coords X Y", json_output, code="INVALID_INPUT")
        return

    backend = _get_backend(json_output)
    x, y = coords

    try:
        backend.move_mouse(x, y)
    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    # Record the action
    _record_action("move", {"x": x, "y": y})

    _json_ok({"action": "moved", "x": x, "y": y}, json_output)

