"""Type command — type text with configurable speed and profile."""
from __future__ import annotations

import json
import logging
import sys

import click

import naturo.cli.interaction._common as _common

logger = logging.getLogger(__name__)


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
    help="Input method: normal (SendInput), hardware (Phys32 driver), hook (MinHook injection)",
)
@_common._method_option
@_common._selector_option
@_common._app_id_option
@_common._verify_options
@_common._see_options
@click.option("--raw", is_flag=True, hidden=True, help="Deprecated: text is now literal by default")
@click.option(
    "--interpret-escapes", "-E", is_flag=True,
    help=r"Interpret C-style escape sequences (\t, \n, \r, \\) in text",
)
@click.option("--process-name", "app", default=None, hidden=True, help="")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def type_cmd(text, delay, profile, wpm, press_return, tab_count, escape,
             delete, clear, paste_mode, file_path, restore, on_element, ref_alias, app, pid,
             window_title, hwnd, input_mode, method, selector, app_id, verify, see_after,
             settle, raw, interpret_escapes, json_output) -> None:
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
    app, hwnd, pid = _common._resolve_app_id(app_id, app, hwnd, pid, json_output)
    if app_id and hwnd is None:
        return  # Error already emitted by _resolve_app_id

    # --ref is a hidden deprecated alias for --on (#381)
    if ref_alias and not on_element:
        on_element = ref_alias
    # Handle --file: read content from file
    if file_path:
        import os
        if not os.path.exists(file_path):
            _common._json_err(f"File not found: {file_path}", json_output, code="INVALID_INPUT")
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as exc:
            _common._json_err(str(exc), json_output, code="FILE_ERROR")
            return
        # --file implies --paste
        paste_mode = True

    # --paste without TEXT: paste current clipboard content via Ctrl+V
    if paste_mode and not text:
        text = None  # Signal clipboard-only paste (no text to set)
    elif not text:
        _common._json_err("TEXT argument is required (or use --paste to paste clipboard)",
                  json_output, code="INVALID_INPUT")
        return

    # (#661) Text is typed literally by default — Windows paths like
    # C:\Users\test\report.txt are preserved without corruption.
    # Use --interpret-escapes / -E to opt-in to C-style escape processing
    # (\t → tab, \n → newline, \r → CR, \\ → literal backslash).
    # File-sourced text (--file) already contains real characters.
    if text and not file_path and interpret_escapes:
        text = (
            text.replace("\\\\", "\x00")   # placeholder for literal backslash
            .replace("\\t", "\t")
            .replace("\\n", "\n")
            .replace("\\r", "\r")
            .replace("\x00", "\\")          # restore literal backslashes
        )

    if wpm < 1:
        _common._json_err(f"--wpm must be >= 1, got {wpm}", json_output, code="INVALID_INPUT")
        return

    # (#960) Opt-in input-content safety guard. When NATURO_SAFE_INPUT=1 is set
    # (the unattended QA loop), refuse to inject text that looks like a shell
    # command — a SendInput focus race could otherwise deliver a destructive
    # fragment (e.g. "$(rm -rf /)") to a terminal. Validates the final resolved
    # content, so it also covers --paste/--file. Normal users (env unset) are
    # unaffected.
    if text is not None:
        from naturo.safety import unsafe_input_reason
        _unsafe = unsafe_input_reason(text)
        if _unsafe:
            _common._json_err(
                f"Refusing to inject unsafe content ({_unsafe}) because "
                f"NATURO_SAFE_INPUT=1 is set. Nothing was typed.",
                json_output,
                code="UNSAFE_INPUT_BLOCKED",
            )
            return

    backend = _common._get_backend(json_output)

    # Auto-routing: detect best interaction method for target app
    route_info = _common._auto_route(app, None, method, json_output)

    # (#230/#612) When --app/--hwnd/--window is specified, focus the target
    # window before typing.  SendInput sends keystrokes to the foreground
    # window, so without focusing first, type silently sends to the wrong
    # window.  Uses backend.focus_window() which employs AttachThreadInput
    # on Windows — raw SetForegroundWindow() fails silently when the caller
    # isn't the foreground process.
    _focused_hwnd = None
    if (app or window_title or hwnd or pid) and not on_element:
        try:
            _target_hwnd = None
            if hasattr(backend, "_resolve_hwnd"):
                _target_hwnd = backend._resolve_hwnd(
                    app=app, window_title=window_title, hwnd=hwnd, pid=pid,
                )
            if _target_hwnd:
                _focused_hwnd = _target_hwnd
                backend.focus_window(hwnd=_target_hwnd)
                # Record the actual PID we focused for accurate routing info
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
                # (#441) Also use UIA SetFocus to restore internal widget
                # focus (e.g. after menu open/close leaves focus on menu bar)
                if hasattr(backend, "focus_element_uia"):
                    try:
                        backend.focus_element_uia(hwnd=_target_hwnd)
                    except Exception as exc:
                        logger.debug("UIA SetFocus failed (hwnd=%s): %s", _target_hwnd, exc)
                import time
                time.sleep(0.15)  # Allow focus to settle
        except Exception as exc:
            _common._json_err(
                f"Failed to focus target window: {exc}. "
                f"Cannot guarantee keystrokes reach '{app or window_title}'.",
                json_output,
                code="WINDOW_FOCUS_ERROR",
            )
            return

    # --selector: resolve unified selector and click to focus before typing (#103)
    if selector and not on_element:
        resolved = _common._resolve_selector_target(
            selector, backend, app, window_title, hwnd, pid, json_output,
        )
        if resolved is None:
            return  # Error already emitted
        try:
            backend.click(resolved[0], resolved[1], button="left", input_mode=input_mode)
            import time
            time.sleep(0.1)  # Brief pause for focus to settle
        except Exception as exc:
            _common._json_err(f"Failed to click selector target: {exc}", json_output)
            return

    # --on: resolve element ref and click to focus before typing (#165)
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
                            click.echo(f"Typing on {on_element} ({_el_desc}) at ({click_x}, {click_y})")
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
            import time
            time.sleep(0.1)  # Brief pause for focus to settle
        except Exception as exc:
            _common._json_err(f"Failed to click target element: {exc}", json_output)
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
                    except Exception as exc:
                        logger.debug("Clipboard backup failed: %s", exc)
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
                    el_result = mgr.resolve_ref_element(on_element, app_name=app)
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
            backend.type_text(text, delay_ms=int(delay), profile=profile,
                              wpm=wpm, input_mode=input_mode)

        if press_return:
            backend.press_key("enter")
        if tab_count:
            for _ in range(tab_count):
                backend.press_key("tab")
        if escape:
            backend.press_key("escape")

    except Exception as exc:
        _common._json_err(str(exc), json_output, exc=exc)
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
        snapshot_data = _common._post_action_see(
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
                except Exception as exc:
                    logger.debug("Clipboard backup failed: %s", exc)
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
                if k in _common._VERIFICATION_KEYS:
                    continue
                click.echo(f"{k}: {v}")
            sys.exit(1)

    # (#426) Inconclusive verification (verified=null) no longer causes
    # exit code 2.  The action was performed — we just can't confirm the
    # UI effect.  Callers can inspect ``verified`` in JSON output.
    _common._json_ok(result_data, json_output)
