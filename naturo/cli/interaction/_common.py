"""Interaction commands: click, type, press (includes hotkey), scroll, drag, move."""
from __future__ import annotations

import json
import logging
import sys
from typing import Callable, Optional

import click

logger = logging.getLogger(__name__)


def _find_element_by_text_fallback(
    backend,
    text: str,
    app: Optional[str] = None,
    hwnd: Optional[int] = None,
    window_title: Optional[str] = None,
    pid: Optional[int] = None,
) -> tuple[int, int] | None:
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


def _see_options(func: Callable) -> Callable:
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


def _verify_options(func: Callable) -> Callable:
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

        def _print_tree(el, indent=0) -> None:
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
    """Append action to active recording (if any)."""
    from naturo.recording import append_step_to_active
    append_step_to_active(command, args, duration_ms)


# ── Method override ──────────────────────────────────────────────────────────

# Valid interaction methods for --method flag.
# "auto" = let the system pick (default); others force a specific channel.
VALID_METHODS = ("auto", "cdp", "uia", "msaa", "ia2", "jab", "vision")


def _method_option(func: Callable) -> Callable:
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


def _selector_option(func: Callable) -> Callable:
    """Shared Click decorator that adds --selector to action commands."""
    return click.option(
        "--selector",
        default=None,
        help=(
            "Unified selector to locate target element. "
            'URI: app://notepad.exe/Button[@name="Save"]. '
            'Short: //Edit[@name="Search"] (any app, descendant search). '
            "App names are flexible: chrome, chrome.exe, Chrome all match."
        ),
    )(func)


def _app_id_option(func: Callable) -> Callable:
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
    stored window handle and PID.  The ``app`` value is left as ``None``
    because the ID map provides precise targeting via hwnd+pid — passing
    the stored process name as ``app`` would trigger fuzzy name matching
    downstream (``_resolve_hwnds``, ``_auto_route``) which fails when the
    stored name is a full path (#573).

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
    # (#752) Auto-detect app ID pattern (a1, a2, ...) in --app flag
    if app_id is None and app is not None:
        from naturo.cli.options import maybe_promote_app_to_app_id
        app, app_id = maybe_promote_app_to_app_id(app, app_id)

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

    # (#573) Return hwnd + pid only.  Do NOT populate app — the stored
    # process_name may be a full path (e.g. "C:\...\chrome.exe") which
    # breaks fuzzy matching in _resolve_hwnds and _auto_route.  The hwnd
    # and pid are sufficient for precise window targeting.
    return None, entry.handle, entry.pid


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
    from naturo.selector import (
        parse, SelectorParseError, SelectorResolver, normalize_app_name,
    )

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

    # Override app from selector if not specified via CLI.
    # Normalize the app name so chrome.exe / Chrome / chrome all work.
    if ast.app and ast.app != "*" and not app:
        app = normalize_app_name(ast.app)

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
        import os

        from naturo.process import _get_process_session_id

        # --------------- session ID for current process ---------------
        sid = _get_process_session_id(os.getpid())
        if sid == -1:
            return False

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
        except Exception as exc:
            logger.debug("Explorer check failed: %s", exc)

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

            # (#565) When --app is explicitly provided but the app was not
            # found (pid=None), fail instead of silently falling back to
            # vision-based click on desktop coordinates.
            if app is not None and result.pid is None:
                _json_err(
                    f"App '{app}' not found among running processes.",
                    json_output,
                    code="APP_NOT_FOUND",
                )
                return {}  # unreachable after sys.exit, but keeps type checker happy

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

