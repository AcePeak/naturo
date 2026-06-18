"""Press and hotkey commands — single keys, combos, or sequential sequences."""
from __future__ import annotations

import logging

import click

import naturo.cli.interaction._common as _common

logger = logging.getLogger(__name__)


def _is_combo(key_str: str) -> bool:
    """Return True if *key_str* looks like a key combination (e.g. ``ctrl+c``)."""
    return "+" in key_str


# Modifier keys that can be pressed standalone (e.g. Alt activates the menu bar).
# These cannot go through key_press() which only handles regular named keys;
# instead they are routed through hotkey() with modifier-only flags.
_MODIFIER_NORMALIZE: dict[str, str] = {
    "alt": "alt", "lalt": "alt", "ralt": "alt",
    "ctrl": "ctrl", "control": "ctrl", "lctrl": "ctrl", "rctrl": "ctrl",
    "shift": "shift", "lshift": "shift", "rshift": "shift",
    "win": "win", "meta": "win", "super": "win",
    "command": "win", "cmd": "win", "lwin": "win", "rwin": "win",
}


def _is_standalone_modifier(key_str: str) -> bool:
    """Return True if *key_str* is a modifier key pressed alone."""
    return key_str.lower().strip() in _MODIFIER_NORMALIZE


def _normalize_modifier(key_str: str) -> str:
    """Normalize a modifier alias to the canonical name used by the bridge."""
    return _MODIFIER_NORMALIZE[key_str.lower().strip()]


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
    help="Input method: normal (SendInput), hardware (Phys32 driver), hook (MinHook injection)",
)
@_common._method_option
@_common._selector_option
@_common._app_id_option
@_common._verify_options
@_common._see_options
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def press(keys: tuple[str, ...], count: int, delay: float, hold_duration: float | None,
          on_element: str | None, ref_alias: str | None, app: str | None, pid: int | None,
          window_title: str | None, hwnd: int | None, input_mode: str, method: str,
          selector: str | None, app_id: str | None, verify: bool, see_after: bool,
          settle: int, json_output: bool) -> None:
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
    app, hwnd, pid = _common._resolve_app_id(app_id, app, hwnd, pid, json_output)
    if app_id and hwnd is None:
        return  # Error already emitted by _resolve_app_id

    # --ref is a hidden deprecated alias for --on (#381)
    if ref_alias and not on_element:
        on_element = ref_alias
    if not keys:
        _common._json_err("Missing argument 'KEY'. Provide a key name (e.g., enter, tab, ctrl+c).",
                  json_output, code="INVALID_INPUT")
        return

    if count < 1:
        _common._json_err(f"--count must be >= 1, got {count}", json_output, code="INVALID_INPUT")
        return

    if hold_duration is not None and hold_duration < 0:
        _common._json_err(f"--hold-duration must be >= 0, got {hold_duration}", json_output, code="INVALID_INPUT")
        return

    import time
    backend = _common._get_backend(json_output)

    # Auto-routing: detect best interaction method for target app
    route_info = _common._auto_route(app, None, method, json_output)

    # --selector: resolve unified selector and click to focus before pressing (#103)
    if selector and not on_element:
        resolved = _common._resolve_selector_target(
            selector, backend, app, window_title, hwnd, pid, json_output,
        )
        if resolved is None:
            return  # Error already emitted
        try:
            backend.click(resolved[0], resolved[1], button="left", input_mode=input_mode)
            time.sleep(0.1)  # Brief pause for focus to settle
        except Exception as exc:
            _common._json_err(f"Failed to click selector target: {exc}", json_output)
            return

    # --on: resolve element ref and click to focus before pressing (#375)
    if on_element:
        import re as _re
        if _re.fullmatch(r"e\d+", on_element):
            from naturo.snapshot import get_snapshot_manager
            mgr = get_snapshot_manager()
            resolved = mgr.resolve_ref(on_element, app_name=app)
            if resolved:
                click_x, click_y = resolved[0], resolved[1]
                if not json_output:
                    try:
                        _el_info = mgr.resolve_ref_element(on_element, app_name=app)
                        if _el_info and len(_el_info) >= 2:
                            _el = _el_info[0]
                            _el_desc = f"{_el.role} \"{_el.title}\"" if _el.title else _el.role
                            click.echo(f"Pressing on {on_element} ({_el_desc}) at ({click_x}, {click_y})")
                    except Exception:
                        pass
            else:
                _common._json_err(
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
                    _common._json_err(
                        f"Element '{on_element}' not found",
                        json_output,
                        code="ELEMENT_NOT_FOUND",
                    )
                    return
            except Exception as exc:
                _common._json_err(str(exc), json_output, exc=exc)
                return
        try:
            backend.click(click_x, click_y, button="left", input_mode=input_mode)
            time.sleep(0.1)  # Brief pause for focus to settle
        except Exception as exc:
            _common._json_err(f"Failed to click target element: {exc}", json_output)
            return

    # (#230/#612/#807) Focus target window before sending key input.
    # SendInput/key_press deliver to the foreground window, so we must
    # ensure the correct window has focus when --app/--hwnd is specified.
    # Uses backend.focus_window() which employs AttachThreadInput on
    # Windows — raw SetForegroundWindow() fails silently when the caller
    # isn't the foreground process.
    if (app or window_title or hwnd or pid) and not on_element:
        try:
            _target_hwnd = None
            if hasattr(backend, "_resolve_hwnd"):
                _target_hwnd = backend._resolve_hwnd(
                    app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                )
            if not _target_hwnd:
                _target_desc = app or window_title or f"PID {pid}" or f"HWND {hwnd}"
                _common._json_err(
                    f"Could not find window for '{_target_desc}'. "
                    "Is the application running and visible?",
                    json_output,
                    code="WINDOW_NOT_FOUND",
                )
                return
            backend.focus_window(hwnd=_target_hwnd)
            # Record actual focused PID for routing accuracy
            try:
                import ctypes
                import ctypes.wintypes
                _focused_pid = ctypes.wintypes.DWORD()
                ctypes.windll.user32.GetWindowThreadProcessId(  # type: ignore[attr-defined]
                    _target_hwnd, ctypes.byref(_focused_pid)
                )
                if route_info and _focused_pid.value:
                    route_info["focused_pid"] = _focused_pid.value
                    route_info["focused_hwnd"] = _target_hwnd
            except Exception as exc:
                logger.debug("PID recording failed (Windows-only): %s", exc)
            # Also try UIA SetFocus for schtasks/remote contexts (#226)
            if hasattr(backend, "focus_element_uia"):
                try:
                    backend.focus_element_uia(hwnd=_target_hwnd)
                except Exception as exc:
                    logger.debug("UIA SetFocus failed (hwnd=%s): %s", _target_hwnd, exc)
            time.sleep(0.15)
        except Exception as exc:
            _common._json_err(
                f"Failed to focus target window: {exc}. "
                f"Cannot guarantee keypresses reach '{app or window_title}'.",
                json_output,
                code="WINDOW_FOCUS_ERROR",
            )
            return

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
                    _common._record_action("hotkey", {"keys": key_list, "hold_duration": hold_duration or 0.05})
                    results.append({"action": "hotkey", "combo": "+".join(key_list)})
                elif _is_standalone_modifier(key_spec):
                    # Standalone modifier keys (alt, ctrl, shift, win) are
                    # routed through hotkey() because key_press() in the DLL
                    # only handles regular named keys.  hotkey() with a
                    # modifier-only bitmask performs press-then-release (#704).
                    backend.hotkey(
                        _normalize_modifier(key_spec),
                        hold_duration_ms=int(hold_duration) if hold_duration else 50,
                        input_mode=input_mode,
                    )
                    _common._record_action("press", {"key": key_spec, "count": 1})
                    results.append({"action": "pressed", "key": key_spec})
                else:
                    backend.press_key(key_spec, input_mode=input_mode)
                    _common._record_action("press", {"key": key_spec, "count": 1})
                    results.append({"action": "pressed", "key": key_spec})
                if rep < count - 1 and delay > 0:
                    time.sleep(delay / 1000.0)
            # Inter-key delay for sequential keys
            if idx < len(keys) - 1 and delay > 0:
                time.sleep(delay / 1000.0)
    except Exception as exc:
        _common._json_err(str(exc), json_output, exc=exc)
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
    help="Input method: normal (SendInput), hardware (Phys32 driver), hook (MinHook injection)",
)
@_common._method_option
@_common._app_id_option
@_common._verify_options
@_common._see_options
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def hotkey(keys, keys_option, hold_duration, app, window_title, hwnd,
           input_mode, method, app_id, verify, see_after, settle, json_output) -> None:
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

    # (#595) Resolve --app-id before delegating to press
    app, hwnd, _pid = _common._resolve_app_id(app_id, app, hwnd, None, json_output)
    if app_id and hwnd is None:
        return

    # Build a single combo string from positional or --keys options
    if keys:
        combo = keys
    elif keys_option:
        combo = "+".join(keys_option)
    else:
        _common._json_err("Specify keys as 'ctrl+c' or via --keys ctrl --keys c", json_output, code="INVALID_INPUT")
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
        app_id=None,  # Already resolved above
        verify=verify,
        see_after=see_after,
        settle=settle,
        json_output=json_output,
    )
