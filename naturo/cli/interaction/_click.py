"""Click command — click on a UI element, text, or coordinates."""
from __future__ import annotations

import logging
from typing import Any

import click

import naturo.cli.interaction._common as _common

logger = logging.getLogger(__name__)


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
@_common._method_option
@_common._selector_option
@_common._app_id_option
@_common._verify_options
@_common._see_options
@click.option("--paste", "paste_after", is_flag=True, help="Paste clipboard after click (Ctrl+V)")
@click.option("--copy", "copy_after", is_flag=True, help="Select all + copy after click (Ctrl+A, Ctrl+C)")
@click.option("--cut", "cut_after", is_flag=True, help="Select all + cut after click (Ctrl+A, Ctrl+X)")
@click.option("--restore/--no-restore", default=True, help="Restore clipboard after --paste (default: True)")
@click.option("--process-name", "app", default=None, hidden=True, help="")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def click_cmd(query: str | None, on_text: str | None, ref_alias: str | None,
              element_id: str | None, coords: tuple[int, int] | None, double: bool,
              right: bool, app: str | None, pid: int | None,
              window_title: str | None, hwnd: int | None, wait_for: float | None,
              input_mode: str, method: str, selector: str | None, app_id: str | None,
              verify: bool, see_after: bool, settle: int,
              paste_after: bool, copy_after: bool, cut_after: bool, restore: bool,
              json_output: bool) -> None:
    """Click on a UI element, text, or coordinates.

    QUERY is optional text or eN ref to find and click on. Use --on, --id, or --coords
    for alternative targeting.

    Input modes (Windows-specific):
      normal   — SendInput API (default, works for most apps)
      hardware — Phys32 driver (bypasses software input filtering)
      hook     — MinHook injection (for protected/game apps)

    Clipboard modifiers (post-click actions):
      --paste  — After clicking, paste clipboard content (Ctrl+V)
      --copy   — After clicking, select all + copy (Ctrl+A, Ctrl+C)
      --cut    — After clicking, select all + cut (Ctrl+A, Ctrl+X)

    \b
    Examples:
      naturo click --coords 500 300
      naturo click --coords 500 300 --right
      naturo click --id "button_ok"
      naturo click e42 --paste
      naturo click e42 --copy
    """
    # --ref is a hidden deprecated alias for --on (#381)
    if ref_alias and not on_text:
        on_text = ref_alias

    # (#361) Resolve --app-id to app/hwnd/pid before any other logic
    app, hwnd, pid = _common._resolve_app_id(app_id, app, hwnd, pid, json_output)
    if app_id and hwnd is None:
        return  # Error already emitted by _resolve_app_id

    backend = _common._get_backend(json_output)

    button = "right" if right else "left"

    # Resolve target coordinates or element_id
    # Priority: --selector (semantic) > --coords > --id > --on/query (#103)
    if selector:
        resolved = _common._resolve_selector_target(
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
        _common._json_err("Specify --selector, --coords X Y, --id, or --on TEXT", json_output, code="INVALID_INPUT")
        return

    # (#448) Resolve eN refs BEFORE auto-routing so we can skip the
    # expensive framework detection chain when we already have cached
    # coordinates from a recent snapshot.
    import re as _re
    _zero_bounds_element = None  # Track element for Invoke fallback (#137)
    _ref_resolved = False  # True when eN ref resolved to coordinates
    _snapshot_hwnd = None  # HWND from snapshot metadata for window focus
    _ref_element = None  # (#681) Cached element metadata for UIA identity lookup
    if target_id and _re.fullmatch(r"e\d+", target_id):
        from naturo.snapshot import get_snapshot_manager
        mgr = get_snapshot_manager()
        _original_ref = target_id  # Save before target_id is cleared
        resolved = mgr.resolve_ref(target_id, app_name=app)
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
            except Exception as exc:
                logger.debug("Snapshot HWND retrieval failed: %s", exc)
            # (#681) Retrieve element metadata (name, role, AutomationId)
            # for identity-based UIA lookup — more reliable than
            # ElementFromPoint for UWP apps where cached coordinates may
            # resolve to the wrong element.
            try:
                el_result = mgr.resolve_ref_element(_original_ref, app_name=app)
                if el_result is not None:
                    _ref_element = el_result[0]  # UIElement
                    # (#662) Show what we're about to click for user verification
                    if not json_output:
                        _el = _ref_element
                        _el_desc = f"{_el.role} \"{_el.title}\"" if _el.title else _el.role
                        click.echo(f"Clicking {_original_ref} ({_el_desc}) at ({x}, {y})")
            except Exception as exc:
                logger.debug("Element metadata retrieval failed: %s", exc)
        else:
            # resolve_ref returns None for both "not found" and "zero-bounds".
            # Check resolve_ref_element to distinguish: if the element exists
            # but has zero-bounds, try UIA Invoke pattern (#137/#135).
            el_result = mgr.resolve_ref_element(target_id, app_name=app)
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
                _common._json_err(
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
            _common._json_err(
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
        route_info = _common._auto_route(app, pid, method, json_output)

    # (#608) Always bring the target window to foreground before clicking
    # when a targeting flag (--app/--hwnd/--pid) is specified or when we
    # have a cached snapshot HWND.  Previous code only activated the window
    # under narrow conditions (UIA routing or cached HWND present), causing
    # clicks to land on the wrong window when the target app was in the
    # background.
    #
    # Uses backend.focus_window() which employs the AttachThreadInput
    # workaround — raw SetForegroundWindow() fails silently when the
    # caller isn't the foreground process.
    _uia_method = route_info.get("method") == "uia" if route_info else False
    _is_uwp = False  # Track UWP apps for UIA click fallback (#248)
    _focus_hwnd = _snapshot_hwnd  # Prefer cached HWND from snapshot
    if not _focus_hwnd and (app or hwnd or pid) and hasattr(backend, "_resolve_hwnd"):
        try:
            _focus_hwnd = backend._resolve_hwnd(
                app=app, window_title=window_title, hwnd=hwnd, pid=pid,
            )
        except Exception as exc:
            logger.debug("HWND resolution for focus failed: %s", exc)
    if _focus_hwnd:
        # Detect UWP/WinUI apps for UIA click fallback (#248, #786)
        if hasattr(backend, "_is_afh_window"):
            try:
                _is_uwp = backend._is_afh_window(_focus_hwnd)
            except Exception as exc:
                logger.debug("UWP detection failed (hwnd=%s): %s", _focus_hwnd, exc)
        # (#786) Standalone WinUI 3 apps (Win11 Notepad, Paint) also need
        # UIA click path but are not hosted by ApplicationFrameHost.
        if not _is_uwp and hasattr(backend, "_is_winui_window"):
            try:
                _is_uwp = backend._is_winui_window(_focus_hwnd)
            except Exception as exc:
                logger.debug("WinUI detection failed (hwnd=%s): %s", _focus_hwnd, exc)
        try:
            backend.focus_window(hwnd=_focus_hwnd)
        except Exception as exc:
            logger.debug("Window focus failed (hwnd=%s): %s", _focus_hwnd, exc)

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
                _common._json_err(
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
                # button has UIA Name "Clear" (清除 on Chinese Windows)).
                fallback = _common._find_element_by_text_fallback(
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
            # (#681) Pass element metadata from snapshot for identity-based
            # lookup — avoids ElementFromPoint returning the wrong element.
            _used_uia_click = False
            if _is_uwp and x is not None and y is not None and button == "left" and not double:
                if hasattr(backend, "click_element_uia"):
                    _uia_kwargs: dict[str, Any] = {"x": x, "y": y, "app": app, "hwnd": hwnd}
                    if _ref_element is not None:
                        _uia_kwargs["element_name"] = _ref_element.title
                        _uia_kwargs["element_automation_id"] = _ref_element.identifier
                        _uia_kwargs["element_role"] = _ref_element.role
                    _used_uia_click = backend.click_element_uia(**_uia_kwargs)
                    if _used_uia_click:
                        logger.info("UWP click: used UIA pattern at (%d, %d)", x, y)
            if not _used_uia_click:
                backend.click(x=x, y=y, button=button, double=double,
                              input_mode=input_mode)
    except Exception as exc:
        _common._json_err(str(exc), json_output)
        return

    # (#168) Clipboard modifiers: --paste, --copy, --cut (post-click actions)
    _clipboard_action = None
    if paste_after or copy_after or cut_after:
        import time
        time.sleep(0.1)  # Brief settle after click
        try:
            if paste_after:
                # Save clipboard for restore if --restore is on
                _old_clip = ""
                if restore:
                    try:
                        _old_clip = backend.clipboard_get()
                    except Exception as exc:
                        logger.debug("Clipboard backup failed: %s", exc)
                backend.hotkey("ctrl", "v")
                _clipboard_action = "paste"
                # Restore previous clipboard content
                if restore and _old_clip:
                    time.sleep(0.1)
                    backend.clipboard_set(_old_clip)
            elif copy_after:
                backend.hotkey("ctrl", "a")
                time.sleep(0.05)
                backend.hotkey("ctrl", "c")
                _clipboard_action = "copy"
            elif cut_after:
                backend.hotkey("ctrl", "a")
                time.sleep(0.05)
                backend.hotkey("ctrl", "x")
                _clipboard_action = "cut"
        except Exception as exc:
            _common._json_err(f"Click succeeded but clipboard action failed: {exc}",
                      json_output, code="CLIPBOARD_ERROR")
            return

    # Record the action
    _common._record_action("click", {
        "x": x, "y": y, "button": button, "double_click": double,
    })

    action = "double-clicked" if double else "clicked"
    if _zero_bounds_element is not None:
        loc = f"{_zero_bounds_element.title or _zero_bounds_element.role} (via UIA Invoke)"
    else:
        loc = f"({x}, {y})" if coords else (target_id or "element")
    result_data: dict[str, Any] = {"action": action, "target": str(loc), "button": button}
    if _clipboard_action:
        result_data["clipboard_action"] = _clipboard_action
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
        snapshot_data = _common._post_action_see(
            backend=backend, settle_ms=settle,
            app=app, window_title=window_title, hwnd=hwnd,
            json_output=json_output,
        )
        if snapshot_data and json_output:
            result_data["snapshot"] = snapshot_data

    # (#426) Inconclusive verification (verified=null) no longer causes
    # exit code 2.  The action was performed — we just can't confirm the
    # UI effect.  Callers can inspect ``verified`` in JSON output.
    _common._json_ok(result_data, json_output)
