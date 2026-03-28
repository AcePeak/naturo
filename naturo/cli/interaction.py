"""Interaction commands: click, type, press (includes hotkey), scroll, drag, move."""
from __future__ import annotations

import json
import logging
import sys
from typing import Optional

import click

logger = logging.getLogger(__name__)


def _find_element_by_text_fallback(
    backend,
    text: str,
    app: Optional[str] = None,
    hwnd: Optional[int] = None,
    window_title: Optional[str] = None,
    pid: Optional[int] = None,
):
    """Fallback element search when C++ exact UIA Name match fails.

    Searches the target app's element tree for elements whose name matches
    the query text.  This handles localized apps where the UIA Name differs
    from the visible text rendered on screen (e.g. Calculator on Chinese
    Windows has UIA Name "清除" but displays "C").  In such apps, the visual
    label is often a child TextBlock element with the abbreviated text as
    its UIA Name.

    Matching priority:
        1. Actionable element (Button, etc.) with exact name match
        2. Any element with exact name match (e.g. child TextBlock)
        3. Actionable element with substring name match

    Args:
        backend: The platform backend instance.
        text: The text to search for.
        app: Application name filter.
        hwnd: Direct window handle.
        window_title: Window title pattern.

    Returns:
        (x, y) center coordinates of the matched element, or None.
    """
    if not hasattr(backend, "get_element_tree"):
        return None

    try:
        tree = backend.get_element_tree(
            app=app, window_title=window_title, hwnd=hwnd, pid=pid, depth=5,
        )
    except Exception as exc:
        logger.debug("Fallback tree search failed to get tree: %s", exc)
        return None

    if tree is None:
        return None

    from naturo.search import search_elements

    matches = search_elements(
        tree, text, actionable_only=False, max_results=50,
    )
    if not matches:
        return None

    query_lower = text.lower()

    # Actionable control types (buttons, edits, etc.) that can be clicked.
    _ACTIONABLE_ROLES = {
        "button", "edit", "checkbox", "radiobutton", "combobox",
        "listitem", "menuitem", "tab", "link", "hyperlink",
        "slider", "spinbutton", "scrollbar", "treeitem",
    }

    exact_actionable = []
    exact_any = []
    substring_actionable = []

    for m in matches:
        el = m.element
        # Skip zero-bounds (offscreen/unrendered) elements
        if el.width == 0 and el.height == 0:
            continue
        name_lower = (el.name or "").lower()
        is_actionable = el.role.lower() in _ACTIONABLE_ROLES
        if name_lower == query_lower:
            if is_actionable:
                exact_actionable.append(el)
            else:
                exact_any.append(el)
        elif is_actionable:
            substring_actionable.append(el)

    best = None
    if exact_actionable:
        best = exact_actionable[0]
    elif exact_any:
        best = exact_any[0]
    elif substring_actionable:
        best = substring_actionable[0]

    if best is None:
        return None

    cx = best.x + best.width // 2
    cy = best.y + best.height // 2
    logger.info(
        "Fallback tree search matched %r → [%s] %r at (%d, %d)",
        text, best.role, best.name, cx, cy,
    )
    return (cx, cy)


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


def _verify_options(func):
    """Shared Click decorator that adds --verify/--no-verify to action commands.

    Post-action verification checks whether the action actually had effect.
    Default is ON — naturo must never lie about success (#231).
    """
    func = click.option(
        "--verify/--no-verify",
        default=True,
        help="Verify action had effect (default: on). Use --no-verify to skip.",
        show_default=True,
    )(func)
    return func


def _post_action_see(
    backend,
    settle_ms: int,
    app: str | None,
    window_title: str | None,
    hwnd: int | None,
    json_output: bool,
    depth: int = 7,
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

    # Store snapshot with ref mapping (inherit active session via NATURO_SESSION)
    from naturo.snapshot import get_snapshot_manager
    from naturo.models.snapshot import UIElement

    mgr = get_snapshot_manager()
    snapshot_id = mgr.create_snapshot()

    ui_map = {}
    _ref_seq = [0]
    ref_map = {}

    import re as _re_mod

    def _flatten(el, parent_id=None):
        _ref_seq[0] += 1
        ref = f"e{_ref_seq[0]}"
        props = getattr(el, "properties", {})
        # (#237) Preserve real AutomationId in identifier, filter
        # tree-assigned "eN" IDs (same logic as core.py _flatten).
        _raw_id = str(el.id) if el.id else None
        if _raw_id and _re_mod.fullmatch(r"e\d+", _raw_id):
            _raw_id = None
        # Use ref as canonical key to avoid overwrites when multiple
        # elements share the same backend AutomationId.
        child_refs = []
        for child in el.children:
            child_refs.append(_flatten(child, parent_id=ref))
        ui_map[ref] = UIElement(
            id=ref,
            element_id=f"element_{ref}",
            role=el.role,
            title=el.name,
            label=el.name,
            value=el.value,
            identifier=_raw_id,
            frame=(el.x, el.y, el.width, el.height),
            is_actionable=getattr(el, "is_actionable", False),
            parent_id=parent_id,
            children=child_refs,
            keyboard_shortcut=props.get("keyboard_shortcut"),
        )
        ref_map[ref] = el.id
        return ref

    _flatten(tree)
    mgr.store_detection_result(snapshot_id, ui_map)
    mgr.store_ref_map(snapshot_id, ref_map)

    if json_output:
        # (#237) Use sequential counter matching _flatten() DFS order for
        # unique display IDs (same fix as core.py to_dict).
        _json_ref_seq = [0]

        def _to_dict(el):
            _json_ref_seq[0] += 1
            display_id = f"e{_json_ref_seq[0]}"
            d = {
                "id": display_id,
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

        click.echo("\n--- UI snapshot (updated) ---")
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


# ── Selector support (#103) ──────────────────────────────────────────────────


def _selector_option(func):
    """Shared Click decorator that adds --selector to action commands."""
    return click.option(
        "--selector",
        default=None,
        help=(
            "Unified selector to locate target element. "
            'URI format: app://notepad.exe/Button[@name="Save"]. '
            'XML format: <selector app="notepad.exe"><node role="Button" name="Save"/></selector>.'
        ),
    )(func)


def _app_id_option(func):
    """Shared Click decorator that adds --app-id to action commands.

    Accepts a stable app/window ID (e.g. ``a1``) assigned by ``naturo app list``.
    When provided, overrides ``--app``, ``--hwnd``, and ``--pid`` with the
    stored values from the ID map.  Priority: --app-id > --hwnd > --pid > --app.
    """
    return click.option(
        "--app-id",
        "app_id",
        default=None,
        help='Stable app/window ID from "naturo app list" output (e.g. a1)',
    )(func)


def _resolve_app_id(
    app_id: Optional[str],
    app: Optional[str],
    hwnd: Optional[int],
    pid: Optional[int],
    json_output: bool,
) -> tuple:
    """Resolve --app-id to (app, hwnd, pid) overrides.

    If ``app_id`` is provided, looks up the stored ID map and returns the
    stored process name and window handle.  Otherwise returns the original
    values unchanged.

    Args:
        app_id: The stable ID string (e.g. "a1"), or None.
        app: Current --app value.
        hwnd: Current --hwnd value.
        pid: Current --pid value.
        json_output: Whether to emit JSON error output.

    Returns:
        Tuple of (app, hwnd, pid) — possibly overridden from the ID map.
        Returns (None, None, None) with error emitted if ID is invalid.
    """
    if app_id is None:
        return app, hwnd, pid

    from naturo.app_ids import get_app_id_map

    id_map = get_app_id_map()
    entry = id_map.resolve(app_id)
    if entry is None:
        _json_err(
            f'App ID "{app_id}" not found or expired. Run "naturo app list" to refresh.',
            json_output,
            code="APP_ID_NOT_FOUND",
        )
        return None, None, None

    return entry.process_name, entry.handle, entry.pid


def _elementinfo_to_dict(el) -> dict:
    """Convert an ElementInfo object to a dict for SelectorResolver.

    Args:
        el: ElementInfo object from the backend.

    Returns:
        Dict with keys expected by SelectorResolver: role, name,
        automationid, cls, value, x, y, width, height, children.
    """
    result = {
        "role": el.role,
        "name": el.name or "",
        "automationid": getattr(el, "id", "") or "",
        "value": el.value or "",
        "x": el.x,
        "y": el.y,
        "width": el.width,
        "height": el.height,
    }
    # Include className if available in properties
    props = getattr(el, "properties", {}) or {}
    cls = props.get("className", "") or props.get("cls", "")
    if cls:
        result["cls"] = cls
    # Recursively convert children
    children = getattr(el, "children", []) or []
    result["children"] = [_elementinfo_to_dict(c) for c in children]
    return result


def _resolve_selector_target(
    selector_str: str,
    backend,
    app: Optional[str],
    window_title: Optional[str],
    hwnd: Optional[int],
    pid: Optional[int],
    json_output: bool,
) -> Optional[tuple]:
    """Resolve a unified selector to (x, y) coordinates.

    Parses the selector string, fetches the UI element tree from the
    backend, and resolves the selector to a target element's center
    coordinates.

    Args:
        selector_str: Selector string (URI or XML format).
        backend: Platform backend instance.
        app: Application name filter.
        window_title: Window title filter.
        hwnd: Window handle.
        pid: Process ID.
        json_output: Whether to emit JSON errors.

    Returns:
        (x, y) center coordinates of the resolved element, or None on failure.
        On failure, emits an appropriate error message.
    """
    from naturo.selector import parse, SelectorParseError, SelectorResolver

    # Parse the selector
    try:
        ast = parse(selector_str)
    except SelectorParseError as exc:
        _json_err(
            f"Invalid selector: {exc}",
            json_output,
            code="INVALID_SELECTOR",
        )
        return None

    # Override app from selector if not specified via CLI
    if ast.app and ast.app != "*" and not app:
        app = ast.app

    # Get element tree
    if not hasattr(backend, "get_element_tree"):
        _json_err(
            "Selector resolution requires a backend with UI tree support",
            json_output,
            code="BACKEND_ERROR",
        )
        return None

    try:
        tree = backend.get_element_tree(
            app=app, window_title=window_title, hwnd=hwnd, pid=pid,
            depth=20,
        )
    except Exception as exc:
        _json_err(
            f"Failed to get UI tree for selector resolution: {exc}",
            json_output,
            code="TREE_ERROR",
        )
        return None

    if tree is None:
        _json_err(
            "No window found for selector resolution. "
            "Check that the target application is running and visible.",
            json_output,
            code="WINDOW_NOT_FOUND",
        )
        return None

    # Convert ElementInfo tree to dict tree for the resolver
    tree_dict = [_elementinfo_to_dict(tree)]

    # Resolve
    resolver = SelectorResolver()
    result = resolver.resolve(ast, tree_dict)

    if result is None:
        _json_err(
            f"Selector matched no elements: {selector_str}",
            json_output,
            code="SELECTOR_NOT_FOUND",
        )
        return None

    el = result.element
    x = el.get("x", 0) + el.get("width", 0) // 2
    y = el.get("y", 0) + el.get("height", 0) // 2

    if el.get("width", 0) == 0 and el.get("height", 0) == 0:
        _json_err(
            f"Selector matched element with zero bounds (offscreen/unrendered): "
            f"{selector_str}",
            json_output,
            code="ZERO_BOUNDS",
        )
        return None

    logger.info(
        "Selector resolved: %r → [%s] %r at (%d, %d) (quality: %s)",
        selector_str, el.get("role", "?"), el.get("name", ""),
        x, y, result.match_quality,
    )
    return (x, y)


# ── Shared helper ────────────────────────────────────────────────────────────


def _is_current_session_interactive() -> bool:
    """Check if the current process runs in an active Console or RDP session.

    Uses the Windows Terminal Services (WTS) API purely via ctypes to
    determine whether the session hosting this process is interactive.
    This handles cases where ``SESSIONNAME`` is not set (e.g. Task
    Scheduler ``/it`` tasks) but the process *is* running in a desktop
    session.

    The implementation queries ``WTSQuerySessionInformationW`` for
    ``WTSConnectState`` — no subprocess calls, no ``query session``
    dependency, no encoding or exit-code surprises.

    Returns:
        True if the process session is an active Console or RDP session.
        False otherwise or on any error.
    """
    try:
        import ctypes
        import ctypes.wintypes

        # --------------- session ID for current process ---------------
        pid = ctypes.windll.kernel32.GetCurrentProcessId()  # type: ignore[attr-defined]
        session_id = ctypes.wintypes.DWORD(0)
        ok = ctypes.windll.kernel32.ProcessIdToSessionId(  # type: ignore[attr-defined]
            pid, ctypes.byref(session_id),
        )
        if not ok:
            return False
        sid = session_id.value

        # Session 0 is always the non-interactive services session.
        if sid == 0:
            return False

        # --------------- WTS connect state via pure ctypes ---------------
        WTS_CURRENT_SERVER_HANDLE = 0
        WTSConnectState = 8  # WTS_INFO_CLASS enum value

        # WTS_CONNECTSTATE_CLASS values we consider interactive:
        WTSActive = 0
        WTSConnected = 1  # user connected but not yet logged in — still desktop

        wtsapi32 = ctypes.windll.wtsapi32  # type: ignore[attr-defined]

        buf = ctypes.wintypes.LPWSTR()
        bytes_returned = ctypes.wintypes.DWORD(0)

        ok = wtsapi32.WTSQuerySessionInformationW(
            WTS_CURRENT_SERVER_HANDLE,
            sid,
            WTSConnectState,
            ctypes.byref(buf),
            ctypes.byref(bytes_returned),
        )
        if not ok:
            return False

        try:
            # The buffer holds a single DWORD (connect state enum).
            state = ctypes.cast(buf, ctypes.POINTER(ctypes.wintypes.DWORD)).contents.value
        finally:
            wtsapi32.WTSFreeMemory(buf)

        return state in (WTSActive, WTSConnected)
    except Exception:
        return False


def _check_desktop_session() -> None:
    """Raise NoDesktopSessionError if running without an interactive desktop.

    On Windows, verifies the *current* session has desktop access — not just
    that a desktop exists somewhere on the machine.

    Detection logic:
    1. SESSIONNAME == "Console" or starts with "RDP-Tcp" → interactive desktop, OK.
    2. SESSIONNAME == "Services" → non-interactive, reject.
    3. SESSIONNAME empty/unset → check via WTS API whether the current process
       session is an active Console or RDP session (handles schtasks /it tasks
       that run interactively but do not set SESSIONNAME).  If the WTS check
       fails, fall back to explorer.exe heuristic for a descriptive error.
    4. Any other SESSIONNAME value → assume interactive (e.g., Citrix, VNC).

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

    # Empty/unset SESSIONNAME — could be SSH, headless service, or schtasks /it
    if not session:
        # First, check if the *current* process session is an active
        # Console or RDP session via WTS API.  Task Scheduler /it tasks
        # run in the interactive session but do NOT set SESSIONNAME.
        if _is_current_session_interactive():
            return

        # Not in an interactive session — check explorer as a hint for
        # a better error message.
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


_VERIFICATION_KEYS = frozenset({
    "verified",
    "verification_detail",
    "verification_method",
    "verification_ms",
    "verification_error",
})
"""Keys that should only appear in JSON output, not in default text mode."""


def _json_ok(data: dict, json_output: bool) -> None:
    """Emit success result as JSON or plain text.

    In text mode, verification internals (verified, verification_detail, etc.)
    are suppressed — they are useful for machine consumers but confusing for
    end users (#273).  JSON mode retains all fields.
    """
    if json_output:
        click.echo(json.dumps({"success": True, "data": data}))
    else:
        for k, v in data.items():
            if k in _VERIFICATION_KEYS:
                continue
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
@click.option("--ref", "ref_alias", hidden=True, help="Deprecated alias for --on")
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
@_selector_option
@_app_id_option
@_verify_options
@_see_options
@click.option("--process-name", "app", default=None, hidden=True, help="")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def click_cmd(query, on_text, ref_alias, element_id, coords, double, right, app, pid,
              window_title, hwnd, wait_for, input_mode, method, selector, app_id,
              verify, see_after, settle, json_output):
    """Click on a UI element, text, or coordinates.

    QUERY is optional text or eN ref to find and click on. Use --on, --id, or --coords
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
    # --ref is a hidden deprecated alias for --on (#381)
    if ref_alias and not on_text:
        on_text = ref_alias

    # (#361) Resolve --app-id to app/hwnd/pid before any other logic
    app, hwnd, pid = _resolve_app_id(app_id, app, hwnd, pid, json_output)
    if app_id and app is None:
        return  # Error already emitted by _resolve_app_id

    backend = _get_backend(json_output)

    button = "right" if right else "left"

    # Resolve target coordinates or element_id
    # Priority: --selector (semantic) > --coords > --id > --on/query (#103)
    if selector:
        resolved = _resolve_selector_target(
            selector, backend, app, window_title, hwnd, pid, json_output,
        )
        if resolved is None:
            return  # Error already emitted
        x, y = resolved
        target_id = None
    elif coords:
        x, y = coords
        target_id = None
    elif element_id:
        x, y = None, None
        target_id = element_id
    elif on_text or query:
        # Find element by text
        text_query = on_text or query
        target_id = text_query
        x, y = None, None
    else:
        _json_err("Specify --selector, --coords X Y, --id, or --on TEXT", json_output, code="INVALID_INPUT")
        return

    # (#448) Resolve eN refs BEFORE auto-routing so we can skip the
    # expensive framework detection chain when we already have cached
    # coordinates from a recent snapshot.
    import re as _re
    _zero_bounds_element = None  # Track element for Invoke fallback (#137)
    _ref_resolved = False  # True when eN ref resolved to coordinates
    _snapshot_hwnd = None  # HWND from snapshot metadata for window focus
    if target_id and _re.fullmatch(r"e\d+", target_id):
        from naturo.snapshot import get_snapshot_manager
        mgr = get_snapshot_manager()
        resolved = mgr.resolve_ref(target_id)
        if resolved:
            x, y = resolved[0], resolved[1]
            _snap_id = resolved[2]
            target_id = None  # use coordinates instead
            _ref_resolved = True
            # (#448) Retrieve the snapshot's stored HWND so we can focus
            # the target window without re-enumerating processes.
            try:
                snapshot = mgr.get_snapshot(_snap_id)
                if snapshot.window_handle:
                    _snapshot_hwnd = snapshot.window_handle
            except Exception:
                pass
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

    # (#533) Validate --app filter even when eN ref resolved from cache.
    # Without this check, `click --app doesnotexist e1` silently clicks
    # the cached element from a previous snapshot — potentially in the
    # wrong application.
    if _ref_resolved and app and hasattr(backend, "_resolve_hwnds"):
        hwnds = backend._resolve_hwnds(app=app)
        if not hwnds:
            _json_err(
                f"No windows found for app '{app}'.",
                json_output,
                code="WINDOW_NOT_FOUND",
            )
            return

    # (#448) Skip auto-routing when eN ref already resolved to cached
    # coordinates — the framework detection chain is unnecessary since
    # we'll use coordinate-based SendInput.
    if _ref_resolved:
        route_info = {}
    else:
        route_info = _auto_route(app, pid, method, json_output)

    # (#226) When UIA routing is active and --app is specified, ensure
    # the target window has focus via UIA before sending mouse input.
    # (#448) When eN ref resolved, use the snapshot's stored HWND for
    # focus instead of re-enumerating processes.
    _uia_method = route_info.get("method") == "uia" if route_info else False
    _is_uwp = False  # Track UWP apps for UIA click fallback (#248)
    if _ref_resolved and _snapshot_hwnd:
        # Fast path: use cached HWND from snapshot for window focus
        try:
            import ctypes
            SW_RESTORE = 9
            if hasattr(backend, "_is_iconic") and backend._is_iconic(_snapshot_hwnd):
                ctypes.windll.user32.ShowWindow(_snapshot_hwnd, SW_RESTORE)
            ctypes.windll.user32.SetForegroundWindow(_snapshot_hwnd)
        except Exception as exc:
            logger.debug("Snapshot HWND focus failed (hwnd=%s): %s", _snapshot_hwnd, exc)
    elif _uia_method and (app or hwnd or pid) and hasattr(backend, "focus_element_uia"):
        try:
            _target_hwnd = backend._resolve_hwnd(app=app, window_title=window_title, hwnd=hwnd, pid=pid)
            if _target_hwnd:
                # Detect if target is a UWP app (#248)
                if hasattr(backend, "_is_applicationframehost"):
                    _is_uwp = backend._is_applicationframehost(_target_hwnd)
                import ctypes
                SW_RESTORE = 9
                if backend._is_iconic(_target_hwnd):
                    ctypes.windll.user32.ShowWindow(_target_hwnd, SW_RESTORE)
                ctypes.windll.user32.SetForegroundWindow(_target_hwnd)
        except Exception as exc:
            logger.debug("UIA focus for click failed: %s", exc)

    # (#231) Capture before-state for post-action verification
    _before_state = None
    if verify:
        try:
            from naturo.verify import capture_before_state
            _before_state = capture_before_state(
                backend,
                action="click",
                app=app,
                window_title=window_title,
                hwnd=hwnd,
                pid=pid,
            )
        except Exception as exc:
            logger.debug("Pre-click state capture failed: %s", exc)

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
            try:
                # (#525) Pass resolved hwnd so find_element searches the
                # correct window, not just the foreground window.
                backend.click(element_id=target_id, button=button, double=double,
                              input_mode=input_mode, hwnd=hwnd)
            except Exception:
                # (#442) Fallback: search the app's element tree when C++
                # exact UIA Name match fails.  Handles localized apps where
                # UIA Name differs from visible text (e.g. Calculator "C"
                # button has UIA Name "清除").
                fallback = _find_element_by_text_fallback(
                    backend, target_id,
                    app=app, hwnd=hwnd, window_title=window_title,
                    pid=pid,
                )
                if fallback is None:
                    raise
                x, y = fallback
                backend.click(x=x, y=y, button=button, double=double,
                              input_mode=input_mode)
        else:
            # (#248) UWP apps: SendInput clicks don't reach content inside
            # ApplicationFrameHost.  Try UIA InvokePattern first for
            # coordinate-based clicks on UWP apps.
            _used_uia_click = False
            if _is_uwp and x is not None and y is not None and button == "left" and not double:
                if hasattr(backend, "click_element_uia"):
                    _used_uia_click = backend.click_element_uia(
                        x=x, y=y, app=app, hwnd=hwnd,
                    )
                    if _used_uia_click:
                        logger.info("UWP click: used UIA InvokePattern at (%d, %d)", x, y)
            if not _used_uia_click:
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
    # (#248) Indicate UIA click was used for UWP apps
    if _is_uwp and locals().get("_used_uia_click"):
        result_data["uwp_uia_click"] = True
    if route_info:
        result_data["routing"] = route_info

    # (#231) Post-action verification
    _verification = None
    if verify:
        try:
            from naturo.verify import verify_click
            _before_focus = _before_state.get("focus") if _before_state else None
            _before_ui_texts = _before_state.get("ui_texts") if _before_state else None
            # (#270) When UIA Invoke pattern was used successfully for UWP
            # apps, pass that as a signal — the Invoke call itself is
            # strong evidence the click worked.
            _uia_invoked = bool(
                _is_uwp and locals().get("_used_uia_click")
            )
            _verification = verify_click(
                backend,
                x=x,
                y=y,
                target_id=target_id,
                app=app,
                window_title=window_title,
                hwnd=hwnd,
                before_focus=_before_focus,
                before_ui_texts=_before_ui_texts,
                uia_invoked=_uia_invoked,
            )
        except Exception as exc:
            logger.debug("Click verification failed: %s", exc)
            from naturo.verify import unknown_result
            _verification = unknown_result(str(exc))
    else:
        from naturo.verify import skip_result
        _verification = skip_result()

    if _verification:
        result_data.update(_verification.to_dict())

    # --see: re-capture UI tree after action
    if see_after:
        snapshot_data = _post_action_see(
            backend=backend, settle_ms=settle,
            app=app, window_title=window_title, hwnd=hwnd,
            json_output=json_output,
        )
        if snapshot_data and json_output:
            result_data["snapshot"] = snapshot_data

    # (#426) Inconclusive verification (verified=null) no longer causes
    # exit code 2.  The action was performed — we just can't confirm the
    # UI effect.  Callers can inspect ``verified`` in JSON output.
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
@click.option("--on", "on_element", help="Target element (eN ref or text label) — click to focus before typing")
@click.option("--ref", "ref_alias", hidden=True, help="Deprecated alias for --on")
@click.option("--app", help="Target application (name or partial match)")
@click.option("--pid", type=int, help="Process ID")
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
@_selector_option
@_app_id_option
@_verify_options
@_see_options
@click.option("--process-name", "app", default=None, hidden=True, help="")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def type_cmd(text, delay, profile, wpm, press_return, tab_count, escape,
             delete, clear, paste_mode, file_path, restore, on_element, ref_alias, app, pid,
             window_title, hwnd, input_mode, method, selector, app_id, verify, see_after,
             settle, json_output):
    """Type text with configurable speed and profile.

    TEXT is the string to type. Supports human-like variable-speed typing
    and Windows-specific input modes.

    Use --paste to set clipboard and Ctrl+V instead of keystroke typing.
    Use --paste without TEXT to paste current clipboard content.
    Use --file with --paste to read content from a file.
    Use --on to target a specific element (click to focus before typing).
    Use --selector with a unified selector to target by semantic path.

    \b
    Examples:
      naturo type "Hello World"
      naturo type "Hello" --return
      naturo type "text" --profile human --wpm 60
      naturo type "large content" --paste
      naturo type --paste --file mytext.txt
      naturo type --paste                        # paste current clipboard
      naturo type "hello" --on e42               # click e42 then type
      naturo type "hello" --on e42 --app feishu  # target app + element
      naturo type "hello" --selector 'app://notepad.exe/Edit[@automationid="15"]'
    """
    # (#361) Resolve --app-id to app/hwnd/pid before any other logic
    app, hwnd, pid = _resolve_app_id(app_id, app, hwnd, pid, json_output)
    if app_id and app is None:
        return  # Error already emitted by _resolve_app_id

    # --ref is a hidden deprecated alias for --on (#381)
    if ref_alias and not on_element:
        on_element = ref_alias
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

    # --paste without TEXT: paste current clipboard content via Ctrl+V
    if paste_mode and not text:
        text = None  # Signal clipboard-only paste (no text to set)
    elif not text:
        _json_err("TEXT argument is required (or use --paste to paste clipboard)",
                  json_output, code="INVALID_INPUT")
        return

    # Interpret C-style escape sequences (\t, \n, \r, \\) in text so that
    # shell-provided literal backslash+letter sequences become real whitespace
    # characters.  File-sourced text (--file) already contains real characters,
    # so skip processing for that path.
    if text and not file_path:
        text = (
            text.replace("\\\\", "\x00")   # placeholder for literal backslash
            .replace("\\t", "\t")
            .replace("\\n", "\n")
            .replace("\\r", "\r")
            .replace("\x00", "\\")          # restore literal backslashes
        )

    if wpm < 1:
        _json_err(f"--wpm must be >= 1, got {wpm}", json_output, code="INVALID_INPUT")
        return

    backend = _get_backend(json_output)

    # Auto-routing: detect best interaction method for target app
    route_info = _auto_route(app, None, method, json_output)

    # (#230) When --app/--hwnd/--window is specified, focus the target window
    # before typing. SendInput sends keystrokes to the foreground window, so
    # without focusing first, type silently sends to the wrong window.
    # Session-aware: _resolve_hwnd now prefers interactive session windows.
    _focused_hwnd = None
    if (app or window_title or hwnd or pid) and not on_element:
        import platform as _plat
        if _plat.system() == "Windows":
            try:
                _target_hwnd = backend._resolve_hwnd(
                    app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                )
                if _target_hwnd:
                    _focused_hwnd = _target_hwnd
                    import ctypes
                    import ctypes.wintypes
                    SW_RESTORE = 9
                    if backend._is_iconic(_target_hwnd):
                        ctypes.windll.user32.ShowWindow(_target_hwnd, SW_RESTORE)
                    ctypes.windll.user32.SetForegroundWindow(_target_hwnd)
                    # Record the actual PID we focused for accurate routing info
                    _focused_pid = ctypes.wintypes.DWORD()
                    ctypes.windll.user32.GetWindowThreadProcessId(
                        _target_hwnd, ctypes.byref(_focused_pid)
                    )
                    if route_info and _focused_pid.value:
                        route_info["focused_pid"] = _focused_pid.value
                        route_info["focused_hwnd"] = _target_hwnd
                    # (#441) Also use UIA SetFocus to restore internal widget
                    # focus (e.g. after menu open/close leaves focus on menu bar)
                    if hasattr(backend, "focus_element_uia"):
                        try:
                            backend.focus_element_uia(hwnd=_target_hwnd)
                        except Exception:
                            pass
                    import time
                    time.sleep(0.15)  # Allow focus to settle
            except Exception as exc:
                _json_err(
                    f"Failed to focus target window: {exc}. "
                    f"Cannot guarantee keystrokes reach '{app or window_title}'.",
                    json_output,
                    code="WINDOW_FOCUS_ERROR",
                )
                return

    # --selector: resolve unified selector and click to focus before typing (#103)
    if selector and not on_element:
        resolved = _resolve_selector_target(
            selector, backend, app, window_title, hwnd, pid, json_output,
        )
        if resolved is None:
            return  # Error already emitted
        try:
            backend.click(resolved[0], resolved[1], button="left", input_mode=input_mode)
            import time
            time.sleep(0.1)  # Brief pause for focus to settle
        except Exception as exc:
            _json_err(f"Failed to click selector target: {exc}", json_output)
            return

    # --on: resolve element ref and click to focus before typing (#165)
    if on_element:
        import re as _re
        if _re.fullmatch(r"e\d+", on_element):
            from naturo.snapshot import get_snapshot_manager
            mgr = get_snapshot_manager()
            resolved = mgr.resolve_ref(on_element)
            if resolved:
                click_x, click_y = resolved[0], resolved[1]
            else:
                _json_err(
                    f"Element ref '{on_element}' not found. Run 'naturo see' first to "
                    f"capture a fresh snapshot, then use the eN ref within 10 minutes.",
                    json_output,
                    code="REF_NOT_FOUND",
                )
                return
        else:
            # Text-based element lookup via backend
            try:
                elem = backend.find_element(on_element)
                if elem:
                    click_x = elem.x + elem.width // 2
                    click_y = elem.y + elem.height // 2
                else:
                    _json_err(
                        f"Element '{on_element}' not found",
                        json_output,
                        code="ELEMENT_NOT_FOUND",
                    )
                    return
            except Exception as exc:
                _json_err(str(exc), json_output)
                return
        try:
            backend.click(click_x, click_y, button="left", input_mode=input_mode)
            import time
            time.sleep(0.1)  # Brief pause for focus to settle
        except Exception as exc:
            _json_err(f"Failed to click target element: {exc}", json_output)
            return

    # (#231) Capture before-state for post-action verification
    _before_state = None
    if verify:
        try:
            from naturo.verify import capture_before_state
            _before_state = capture_before_state(
                backend,
                action="type",
                ref=on_element if on_element else None,
                app=app,
                window_title=window_title,
                hwnd=hwnd,
                pid=pid,
            )
        except Exception as exc:
            logger.debug("Pre-type state capture failed: %s", exc)

    try:
        if clear:
            backend.hotkey("ctrl", "a")
            backend.press_key("delete")
        elif delete:
            import warnings
            warnings.warn(
                "naturo type --delete is deprecated and will be removed in a "
                "future release. Use --clear instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            # Behave like --clear: select all then delete (#371)
            backend.hotkey("ctrl", "a")
            backend.press_key("delete")

        # Determine if UIA-based input should be attempted (#226).
        # When routing detects UIA for the target app, try UIA ValuePattern
        # first — it works in schtasks/remote contexts where SendInput fails
        # silently.
        _uia_method = route_info.get("method") == "uia" if route_info else False
        _used_uia = False

        if paste_mode:
            if text is not None:
                # Text provided: save clipboard → set text → Ctrl+V → restore
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
                # No text: paste current clipboard content directly (#165)
                backend.hotkey("ctrl", "v")
        elif _uia_method and text and "\n" not in text and "\r" not in text and hasattr(backend, "set_element_value"):
            # UIA ValuePattern path (#226): bypasses SendInput entirely.
            # Resolves target HWND from --app and sets text directly on the
            # focused or first editable element in the window.
            #
            # Skip when text contains newline/CR (#563): UIA SetValue()
            # silently strips these characters, causing a silent failure.
            # SendInput handles them correctly as Enter keypresses.
            _target_hwnd = 0
            _target_name = None
            _target_aid = None
            _target_role = "Edit"  # Default to Edit control

            # Resolve element info from --on ref if available
            if on_element:
                import re as _re
                if _re.fullmatch(r"e\d+", on_element):
                    from naturo.snapshot import get_snapshot_manager
                    mgr = get_snapshot_manager()
                    el_result = mgr.resolve_ref_element(on_element)
                    if el_result:
                        elem, _snap = el_result
                        _target_name = elem.title or elem.label
                        _target_aid = elem.identifier
                        _target_role = elem.role

            # Resolve HWND from --app
            if app or window_title or hwnd or pid:
                try:
                    _target_hwnd = backend._resolve_hwnd(
                        app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                    )
                except Exception:
                    _target_hwnd = 0

            _used_uia = backend.set_element_value(
                text=text,
                hwnd=_target_hwnd,
                name=_target_name,
                automation_id=_target_aid,
                role=_target_role,
            )
            if not _used_uia:
                # UIA SetValue failed — fall back to SendInput
                logger.debug("UIA SetValue failed, falling back to SendInput")
                backend.type_text(text, delay_ms=int(delay), profile=profile,
                                  wpm=wpm, input_mode=input_mode)
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
    display_text = text if text is not None else "(clipboard)"
    display_len = len(text) if text is not None else 0
    result_data = {"action": action, "text": display_text, "length": display_len}
    if _used_uia:
        result_data["input_method"] = "uia_set_value"
    if on_element:
        result_data["target"] = on_element
    if route_info:
        result_data["routing"] = route_info

    # (#231) Post-action verification
    _verification = None
    if verify:
        try:
            from naturo.verify import verify_type, skip_result
            _before_value = _before_state.get("value") if _before_state else None
            _before_ui_texts = _before_state.get("ui_texts") if _before_state else None
            _verification = verify_type(
                backend,
                text=text,
                ref=on_element if on_element else None,
                app=app,
                window_title=window_title,
                hwnd=hwnd,
                before_value=_before_value,
                before_ui_texts=_before_ui_texts,
                paste_mode=paste_mode,
            )
        except Exception as exc:
            logger.debug("Type verification failed: %s", exc)
            from naturo.verify import unknown_result
            _verification = unknown_result(str(exc))
    else:
        from naturo.verify import skip_result
        _verification = skip_result()

    if _verification:
        result_data.update(_verification.to_dict())

    # --see: re-capture UI tree after action
    if see_after:
        snapshot_data = _post_action_see(
            backend=backend, settle_ms=settle,
            app=app, window_title=window_title, hwnd=hwnd,
            json_output=json_output,
        )
        if snapshot_data and json_output:
            result_data["snapshot"] = snapshot_data

    # (#425) Auto-fallback to paste mode when verification detects silent
    # failure and we used SendInput (not paste/UIA).  IME or other input
    # interceptors may swallow keystrokes; clipboard paste bypasses them.
    if (
        _verification
        and _verification.verified is False
        and not paste_mode
        and not _used_uia
        and text is not None
    ):
        logger.debug("Type verification failed — retrying with paste mode (#425)")
        try:
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

            # Re-verify after paste fallback
            from naturo.verify import verify_type
            _verification = verify_type(
                backend,
                text=text,
                ref=on_element if on_element else None,
                app=app,
                window_title=window_title,
                hwnd=hwnd,
                before_value=_before_state.get("value") if _before_state else None,
                before_ui_texts=_before_state.get("ui_texts") if _before_state else None,
                paste_mode=True,
            )
            result_data["action"] = "pasted"
            result_data["fallback"] = "paste_after_type_failure"
            if _verification:
                result_data.update(_verification.to_dict())
        except Exception as exc:
            logger.debug("Paste fallback also failed: %s", exc)

    # (#231) Exit with error if verification detected silent failure
    if _verification and _verification.verified is False:
        if json_output:
            from naturo.cli.error_helpers import json_error
            # Merge verification data into error output
            err_data = json.loads(json_error("VERIFICATION_FAILED", _verification.detail))
            err_data["data"] = result_data
            click.echo(json.dumps(err_data))
            sys.exit(1)
        else:
            click.echo(f"WARNING: {_verification.detail}", err=True)
            for k, v in result_data.items():
                if k in _VERIFICATION_KEYS:
                    continue
                click.echo(f"{k}: {v}")
            sys.exit(1)

    # (#426) Inconclusive verification (verified=null) no longer causes
    # exit code 2.  The action was performed — we just can't confirm the
    # UI effect.  Callers can inspect ``verified`` in JSON output.
    _json_ok(result_data, json_output)


# ── press ────────────────────────────────────────────────────────────────────


def _is_combo(key_str: str) -> bool:
    """Return True if *key_str* looks like a key combination (e.g. ``ctrl+c``)."""
    return "+" in key_str


@click.command()
@click.argument("keys", nargs=-1)
@click.option("--count", "-n", type=int, default=1, help="Number of times to press", show_default=True)
@click.option("--delay", type=float, default=50.0, help="Delay between presses (ms)", show_default=True)
@click.option("--hold-duration", type=float, default=None, help="Hold duration for combos (ms)")
@click.option("--on", "on_element", help="Target element (eN ref or text label) — click to focus before pressing")
@click.option("--ref", "ref_alias", hidden=True, help="Deprecated alias for --on")
@click.option("--app", help="Target application (name or partial match)")
@click.option("--pid", type=int, help="Process ID")
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
@_selector_option
@_app_id_option
@_verify_options
@_see_options
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def press(keys, count, delay, hold_duration, on_element, ref_alias, app, pid, window_title, hwnd, input_mode, method, selector, app_id, verify, see_after, settle, json_output):
    """Press keys — single keys, combos, or sequential key sequences.

    KEYS can be one or more key specs.  A spec containing ``+`` is treated as
    a key combination (like ``ctrl+c``); otherwise it is a single key press.

    \b
    Examples:
      naturo press enter                  # single key
      naturo press tab --count 3          # repeat
      naturo press ctrl+c                 # key combination (was: hotkey)
      naturo press ctrl+a ctrl+c          # sequential combos
      naturo press alt+f4
      naturo press enter --selector 'app://*/Button[@name="OK"]'
    """
    # (#361) Resolve --app-id to app/hwnd/pid before any other logic
    app, hwnd, pid = _resolve_app_id(app_id, app, hwnd, pid, json_output)
    if app_id and app is None:
        return  # Error already emitted by _resolve_app_id

    # --ref is a hidden deprecated alias for --on (#381)
    if ref_alias and not on_element:
        on_element = ref_alias
    if not keys:
        _json_err("Missing argument 'KEY'. Provide a key name (e.g., enter, tab, ctrl+c).",
                  json_output, code="INVALID_INPUT")
        return

    if count < 1:
        _json_err(f"--count must be >= 1, got {count}", json_output, code="INVALID_INPUT")
        return

    if hold_duration is not None and hold_duration < 0:
        _json_err(f"--hold-duration must be >= 0, got {hold_duration}", json_output, code="INVALID_INPUT")
        return

    import time
    backend = _get_backend(json_output)

    # Auto-routing: detect best interaction method for target app
    route_info = _auto_route(app, None, method, json_output)

    # --selector: resolve unified selector and click to focus before pressing (#103)
    if selector and not on_element:
        resolved = _resolve_selector_target(
            selector, backend, app, window_title, hwnd, pid, json_output,
        )
        if resolved is None:
            return  # Error already emitted
        try:
            backend.click(resolved[0], resolved[1], button="left", input_mode=input_mode)
            time.sleep(0.1)  # Brief pause for focus to settle
        except Exception as exc:
            _json_err(f"Failed to click selector target: {exc}", json_output)
            return

    # --on: resolve element ref and click to focus before pressing (#375)
    if on_element:
        import re as _re
        if _re.fullmatch(r"e\d+", on_element):
            from naturo.snapshot import get_snapshot_manager
            mgr = get_snapshot_manager()
            resolved = mgr.resolve_ref(on_element)
            if resolved:
                click_x, click_y = resolved[0], resolved[1]
            else:
                _json_err(
                    f"Element ref '{on_element}' not found. Run 'naturo see' first to "
                    f"capture a fresh snapshot, then use the eN ref within 10 minutes.",
                    json_output,
                    code="REF_NOT_FOUND",
                )
                return
        else:
            # Text-based element lookup via backend
            try:
                elem = backend.find_element(on_element)
                if elem:
                    click_x = elem.x + elem.width // 2
                    click_y = elem.y + elem.height // 2
                else:
                    _json_err(
                        f"Element '{on_element}' not found",
                        json_output,
                        code="ELEMENT_NOT_FOUND",
                    )
                    return
            except Exception as exc:
                _json_err(str(exc), json_output)
                return
        try:
            backend.click(click_x, click_y, button="left", input_mode=input_mode)
            time.sleep(0.1)  # Brief pause for focus to settle
        except Exception as exc:
            _json_err(f"Failed to click target element: {exc}", json_output)
            return

    # (#230) Focus target window before sending key input.
    # SendInput/key_press deliver to the foreground window, so we must
    # ensure the correct window has focus when --app/--hwnd is specified.
    # Session-aware: _resolve_hwnd now prefers interactive session windows.
    if (app or window_title or hwnd or pid) and not on_element:
        import platform as _plat
        if _plat.system() == "Windows":
            try:
                _target_hwnd = backend._resolve_hwnd(
                    app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                )
                if _target_hwnd:
                    import ctypes
                    import ctypes.wintypes
                    SW_RESTORE = 9
                    if backend._is_iconic(_target_hwnd):
                        ctypes.windll.user32.ShowWindow(_target_hwnd, SW_RESTORE)
                    ctypes.windll.user32.SetForegroundWindow(_target_hwnd)
                    # Record actual focused PID for routing accuracy
                    _focused_pid = ctypes.wintypes.DWORD()
                    ctypes.windll.user32.GetWindowThreadProcessId(
                        _target_hwnd, ctypes.byref(_focused_pid)
                    )
                    if route_info and _focused_pid.value:
                        route_info["focused_pid"] = _focused_pid.value
                        route_info["focused_hwnd"] = _target_hwnd
                    # Also try UIA SetFocus for schtasks/remote contexts (#226)
                    if hasattr(backend, "focus_element_uia"):
                        try:
                            backend.focus_element_uia(hwnd=_target_hwnd)
                        except Exception:
                            pass
                    time.sleep(0.15)
            except Exception as exc:
                logger.warning("Failed to focus target window for press: %s", exc)

    # (#231) Capture before-state for post-action verification
    _before_state = None
    if verify:
        try:
            from naturo.verify import capture_before_state
            _before_state = capture_before_state(
                backend,
                action="press",
                ref=on_element if on_element else None,
                app=app,
                window_title=window_title,
                hwnd=hwnd,
                pid=pid,
            )
        except Exception as exc:
            logger.debug("Pre-press state capture failed: %s", exc)

    # Warn when sending Ctrl+C without --app (will kill the calling terminal)
    _sending_ctrl_c = any(
        k.lower().replace(" ", "") in ("ctrl+c", "control+c")
        for k in keys if _is_combo(k)
    )
    if _sending_ctrl_c and not (app or window_title or hwnd):
        import signal
        # Temporarily ignore SIGINT so we don't kill ourselves
        _orig_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    else:
        _orig_handler = None

    results: list[dict] = []
    try:
        for idx, key_spec in enumerate(keys):
            for rep in range(count):
                if _is_combo(key_spec):
                    key_list = [k.strip() for k in key_spec.replace("+", " ").split()]
                    backend.hotkey(
                        *key_list,
                        hold_duration_ms=int(hold_duration) if hold_duration else 50,
                        input_mode=input_mode,
                    )
                    _record_action("hotkey", {"keys": key_list, "hold_duration": hold_duration or 0.05})
                    results.append({"action": "hotkey", "combo": "+".join(key_list)})
                else:
                    backend.press_key(key_spec, input_mode=input_mode)
                    _record_action("press", {"key": key_spec, "count": 1})
                    results.append({"action": "pressed", "key": key_spec})
                if rep < count - 1 and delay > 0:
                    time.sleep(delay / 1000.0)
            # Inter-key delay for sequential keys
            if idx < len(keys) - 1 and delay > 0:
                time.sleep(delay / 1000.0)
    except Exception as exc:
        _json_err(str(exc), json_output)
        return
    finally:
        if _orig_handler is not None:
            import signal
            signal.signal(signal.SIGINT, _orig_handler)

    # Build result — keep backward-compatible shape for single-key usage
    if len(keys) == 1 and not _is_combo(keys[0]):
        result_data = {"action": "pressed", "key": keys[0], "count": count}
    elif len(keys) == 1 and _is_combo(keys[0]):
        combo_keys = [k.strip() for k in keys[0].replace("+", " ").split()]
        result_data = {"action": "hotkey", "combo": "+".join(combo_keys)}
        if count > 1:
            result_data["count"] = count
    else:
        result_data = {"action": "pressed", "sequence": list(keys), "count": count}

    if on_element:
        result_data["target"] = on_element

    if route_info:
        result_data["routing"] = route_info

    # (#231) Post-action verification
    _verification = None
    if verify:
        try:
            from naturo.verify import verify_press
            _before_focus = _before_state.get("focus") if _before_state else None
            _verification = verify_press(
                backend,
                keys=keys,
                app=app,
                window_title=window_title,
                hwnd=hwnd,
                before_focus=_before_focus,
            )
        except Exception as exc:
            logger.debug("Press verification failed: %s", exc)
            from naturo.verify import unknown_result
            _verification = unknown_result(str(exc))
    else:
        from naturo.verify import skip_result
        _verification = skip_result()

    if _verification:
        result_data.update(_verification.to_dict())

    # --see: re-capture UI tree after action
    if see_after:
        snapshot_data = _post_action_see(
            backend=backend, settle_ms=settle,
            app=app, window_title=window_title, hwnd=hwnd,
            json_output=json_output,
        )
        if snapshot_data and json_output:
            result_data["snapshot"] = snapshot_data

    # (#426) Inconclusive verification (verified=null) no longer causes
    # exit code 2.  The action was performed — we just can't confirm the
    # UI effect.  Callers can inspect ``verified`` in JSON output.
    _json_ok(result_data, json_output)


# ── hotkey (hidden alias for press) ──────────────────────────────────────────


@click.command(hidden=True)
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
@_verify_options
@_see_options
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def hotkey(keys, keys_option, hold_duration, app, window_title, hwnd,
           input_mode, method, verify, see_after, settle, json_output):
    """Press a hotkey combination (alias for 'press').

    \b
    Deprecated: use 'naturo press ctrl+c' instead of 'naturo hotkey ctrl+c'.
    This command is kept for backward compatibility.
    """
    if not json_output:
        click.echo(
            "Warning: 'naturo hotkey' is deprecated and will be removed in v0.4.0. "
            "Use 'naturo press' instead.",
            err=True,
        )
    # Build a single combo string from positional or --keys options
    if keys:
        combo = keys
    elif keys_option:
        combo = "+".join(keys_option)
    else:
        _json_err("Specify keys as 'ctrl+c' or via --keys ctrl --keys c", json_output, code="INVALID_INPUT")
        return

    # Delegate to press via Click context invoke
    ctx = click.get_current_context()
    ctx.invoke(
        press,
        keys=(combo,),
        count=1,
        delay=50.0,
        hold_duration=hold_duration,
        app=app,
        window_title=window_title,
        hwnd=hwnd,
        input_mode=input_mode,
        method=method,
        verify=verify,
        see_after=see_after,
        settle=settle,
        json_output=json_output,
    )


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
@click.option("--smooth", is_flag=True, help="Smooth scrolling (Phase 3)")
@click.option("--delay", type=float, help="Delay between scroll steps (ms)")
@click.option("--app", help="Target application (name or partial match)")
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@_selector_option
@_method_option
@_see_options
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def scroll(direction_arg, direction_option, amount, on_text, ref_alias, element_id, coords,
           smooth, delay, app, window_title, hwnd, selector, method, see_after, settle,
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
    direction = direction_arg or direction_option or "down"
    if amount < 1:
        _json_err(f"--amount must be >= 1, got {amount}", json_output, code="INVALID_INPUT")
        return

    backend = _get_backend(json_output)

    # Auto-routing: detect best interaction method for target app
    route_info = _auto_route(app, None, method, json_output)

    # Resolve target coordinates: --selector > --coords > --on/--id
    x, y = None, None
    target_label = None

    if selector:
        resolved = _resolve_selector_target(
            selector, backend, app, window_title, hwnd, None, json_output,
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
@click.option("--window", "window_title", default=None, help="Window title pattern (substring match)")
@click.option("--window-title", "window_title", default=None, hidden=True, help="")
@click.option("--hwnd", type=int, default=None, help="Window handle (HWND)")
@_method_option
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def drag(from_text, from_coords, from_selector, to_text, to_coords, to_selector,
         duration, steps, modifiers, profile, app, window_title, hwnd, method,
         json_output):
    """Drag from one element/position to another.

    \b
    Examples:
      naturo drag --from e5 --to e12
      naturo drag --from-coords 100 100 --to-coords 500 300
      naturo drag --from e5 --to-coords 500 300
      naturo drag --from-selector 'app://*/ListItem[@name="File1"]' --to-selector 'app://*/TreeItem[@name="Folder"]'
    """
    # Resolve element refs (eN) from snapshot for --from and --to (#154)
    import re as _re
    from naturo.snapshot import get_snapshot_manager

    backend = _get_backend(json_output)

    fx, fy = None, None
    tx, ty = None, None
    from_label = None
    to_label = None

    # Resolve source: --from-selector > --from-coords > --from (eN ref)
    if from_selector:
        resolved = _resolve_selector_target(
            from_selector, backend, app, window_title, hwnd, None, json_output,
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
            _json_err(
                f"Source element ref '{from_text}' not found or has zero-size bounds. "
                f"Run 'naturo see' first to capture a fresh snapshot.",
                json_output,
                code="REF_NOT_FOUND",
            )
            return
    else:
        _json_err(
            "Specify source: --from-selector, --from-coords X Y, or --from eN "
            "(element ref from 'naturo see')",
            json_output,
            code="INVALID_INPUT",
        )
        return

    # Resolve destination: --to-selector > --to-coords > --to (eN ref)
    if to_selector:
        resolved = _resolve_selector_target(
            to_selector, backend, app, window_title, hwnd, None, json_output,
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
            _json_err(
                f"Destination element ref '{to_text}' not found or has zero-size bounds. "
                f"Run 'naturo see' first to capture a fresh snapshot.",
                json_output,
                code="REF_NOT_FOUND",
            )
            return
    else:
        _json_err(
            "Specify destination: --to-selector, --to-coords X Y, or --to eN "
            "(element ref from 'naturo see')",
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
@_selector_option
@_method_option
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def move(to_text, coords, element_id, duration, app, window_title, hwnd,
         selector, method, json_output):
    """Move the mouse cursor to a target element or coordinates.

    \b
    Examples:
      naturo move --coords 500 300
      naturo move --selector 'app://*/Button[@name="Save"]'
    """
    backend = _get_backend(json_output)

    # Resolve target: --selector > --coords
    x, y = None, None

    if selector:
        resolved = _resolve_selector_target(
            selector, backend, app, window_title, hwnd, None, json_output,
        )
        if resolved is None:
            return
        x, y = resolved
    elif coords:
        x, y = coords
    else:
        _json_err("Specify --selector, --coords X Y, or --to", json_output, code="INVALID_INPUT")
        return

    try:
        backend.move_mouse(x, y)
    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    # Record the action
    _record_action("move", {"x": x, "y": y})

    _json_ok({"action": "moved", "x": x, "y": y}, json_output)

