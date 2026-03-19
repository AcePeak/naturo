"""Interaction commands: click, type, press, hotkey, scroll, drag, move, paste."""
import json
import platform
import sys

import click

# ── Shared helper ────────────────────────────────────────────────────────────


def _get_backend():
    """Return the platform backend, raising UsageError if unavailable."""
    from naturo.backends.base import get_backend
    try:
        return get_backend()
    except Exception as exc:
        raise click.UsageError(str(exc))


def _json_ok(data: dict, json_output: bool) -> None:
    """Emit success result as JSON or plain text."""
    if json_output:
        click.echo(json.dumps({"ok": True, **data}))
    else:
        for k, v in data.items():
            click.echo(f"{k}: {v}")


def _json_err(msg: str, json_output: bool, exit_code: int = 1) -> None:
    """Emit error result as JSON or plain text, then exit."""
    if json_output:
        click.echo(json.dumps({"ok": False, "error": msg}))
    else:
        click.echo(f"Error: {msg}", err=True)
    sys.exit(exit_code)


# ── click ────────────────────────────────────────────────────────────────────


@click.command("click")
@click.argument("query", required=False)
@click.option("--on", "on_text", help="Text/element to click on")
@click.option("--id", "element_id", help="Automation element ID")
@click.option("--coords", nargs=2, type=int, metavar="X Y", help="X Y coordinates")
@click.option("--double", is_flag=True, help="Double-click")
@click.option("--right", is_flag=True, help="Right-click")
@click.option("--app", help="Application name")
@click.option("--pid", type=int, help="Process ID")
@click.option("--window-title", help="Window title pattern")
@click.option("--window-id", "--hwnd", "window_id", type=int, help="Window handle (HWND)")
@click.option("--wait-for", type=float, help="Wait for element (seconds)")
@click.option(
    "--input-mode",
    type=click.Choice(["normal", "hardware", "hook"]),
    default="normal",
    help="Input method: normal (SendInput), hardware (Phys32 driver), hook (MinHook injection)",
)
@click.option("--process-name", help="Filter by process name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def click_cmd(query, on_text, element_id, coords, double, right, app, pid,
              window_title, window_id, wait_for, input_mode, process_name,
              json_output):
    """Click on a UI element, text, or coordinates.

    QUERY is optional text to find and click on. Use --on, --id, or --coords
    for alternative targeting.

    Input modes (Windows-specific):
      normal   — SendInput API (default, works for most apps)
      hardware — Phys32 driver (bypasses software input filtering)
      hook     — MinHook injection (for protected/game apps)

    Examples:
      naturo click --coords 500 300
      naturo click --coords 500 300 --right
      naturo click --id "button_ok"
    """
    backend = _get_backend()

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
        _json_err("Specify --coords X Y, --id, or --on TEXT", json_output)
        return

    try:
        if target_id:
            backend.click(element_id=target_id, button=button, double=double,
                          input_mode=input_mode)
        else:
            backend.click(x=x, y=y, button=button, double=double,
                          input_mode=input_mode)
    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    action = "double-clicked" if double else "clicked"
    loc = f"({x}, {y})" if coords else (target_id or "element")
    _json_ok({"action": action, "target": str(loc), "button": button}, json_output)


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
@click.option("--app", help="Application name")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle (HWND)")
@click.option(
    "--input-mode",
    type=click.Choice(["normal", "hardware", "hook"]),
    default="normal",
    help="Input method: normal (SendInput), hardware (Phys32), hook (MinHook)",
)
@click.option("--process-name", help="Filter by process name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def type_cmd(text, delay, profile, wpm, press_return, tab_count, escape,
             delete, clear, app, window_title, hwnd, input_mode,
             process_name, json_output):
    """Type text with configurable speed and profile.

    TEXT is the string to type. Supports human-like variable-speed typing
    and Windows-specific input modes.

    Examples:
      naturo type "Hello World"
      naturo type "Hello" --return
      naturo type "text" --profile human --wpm 60
    """
    if not text:
        _json_err("TEXT argument is required", json_output)
        return

    backend = _get_backend()

    try:
        if clear:
            backend.hotkey("ctrl", "a")
            backend.press_key("delete")
        elif delete:
            backend.press_key("delete")

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

    _json_ok({"action": "typed", "text": text, "length": len(text)}, json_output)


# ── press ────────────────────────────────────────────────────────────────────


@click.command()
@click.argument("key")
@click.option("--count", "-n", type=int, default=1, help="Number of times to press", show_default=True)
@click.option("--delay", type=float, default=50.0, help="Delay between presses (ms)", show_default=True)
@click.option("--app", help="Application name")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle (HWND)")
@click.option(
    "--input-mode",
    type=click.Choice(["normal", "hardware", "hook"]),
    default="normal",
    help="Input method",
)
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def press(key, count, delay, app, window_title, hwnd, input_mode, json_output):
    """Press a single key or key sequence.

    KEY can be a key name (enter, tab, escape, f1-f12, a-z, 0-9, etc.)

    Examples:
      naturo press enter
      naturo press tab --count 3
      naturo press f5
    """
    import time
    backend = _get_backend()

    try:
        for i in range(count):
            backend.press_key(key, input_mode=input_mode)
            if i < count - 1 and delay > 0:
                time.sleep(delay / 1000.0)
    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    _json_ok({"action": "pressed", "key": key, "count": count}, json_output)


# ── hotkey ───────────────────────────────────────────────────────────────────


@click.command()
@click.argument("keys", required=False)
@click.option("--keys", "keys_option", multiple=True, help="Key names (repeatable)")
@click.option("--hold-duration", type=float, help="Hold duration in ms")
@click.option("--app", help="Application name")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle (HWND)")
@click.option(
    "--input-mode",
    type=click.Choice(["normal", "hardware", "hook"]),
    default="normal",
    help="Input method",
)
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def hotkey(keys, keys_option, hold_duration, app, window_title, hwnd,
           input_mode, json_output):
    """Press a hotkey combination.

    KEYS as a string like "ctrl+c" or "alt+f4". Or use --keys for each key.

    Examples:
      naturo hotkey ctrl+c
      naturo hotkey ctrl+z
      naturo hotkey --keys ctrl --keys shift --keys z
    """
    backend = _get_backend()

    # Parse key combo from positional arg (e.g. "ctrl+c") or --keys options
    if keys:
        key_list = [k.strip() for k in keys.replace("+", " ").split()]
    elif keys_option:
        key_list = list(keys_option)
    else:
        _json_err("Specify keys as 'ctrl+c' or via --keys ctrl --keys c", json_output)
        return

    try:
        backend.hotkey(*key_list,
                       hold_duration_ms=int(hold_duration) if hold_duration else 50)
    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    combo = "+".join(key_list)
    _json_ok({"action": "hotkey", "combo": combo}, json_output)


# ── scroll ───────────────────────────────────────────────────────────────────


@click.command()
@click.option(
    "--direction", "-d",
    type=click.Choice(["up", "down", "left", "right"]),
    default="down",
    help="Scroll direction",
    show_default=True,
)
@click.option("--amount", "-a", type=int, default=3, help="Scroll amount (notches)", show_default=True)
@click.option("--on", "on_text", help="Element to scroll on")
@click.option("--smooth", is_flag=True, help="Smooth scrolling (Phase 3)")
@click.option("--delay", type=float, help="Delay between scroll steps (ms)")
@click.option("--app", help="Application name")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle (HWND)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def scroll(direction, amount, on_text, smooth, delay, app, window_title,
           hwnd, json_output):
    """Scroll in a direction.

    Examples:
      naturo scroll --direction down --amount 5
      naturo scroll -d up -a 3
    """
    backend = _get_backend()

    try:
        backend.scroll(direction=direction, amount=amount, smooth=smooth)
    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    _json_ok({"action": "scrolled", "direction": direction, "amount": amount}, json_output)


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
@click.option("--app", help="Application name")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle (HWND)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def drag(from_text, from_coords, to_text, to_coords, duration, steps,
         modifiers, profile, app, window_title, hwnd, json_output):
    """Drag from one element/position to another.

    Examples:
      naturo drag --from-coords 100 100 --to-coords 500 300
    """
    if not from_coords:
        _json_err("Specify --from-coords X Y (element-based drag coming in Phase 3)", json_output)
        return
    if not to_coords:
        _json_err("Specify --to-coords X Y", json_output)
        return

    backend = _get_backend()

    fx, fy = from_coords
    tx, ty = to_coords
    duration_ms = int(duration * 1000)

    try:
        backend.drag(from_x=fx, from_y=fy, to_x=tx, to_y=ty,
                     duration_ms=duration_ms, steps=steps)
    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    _json_ok({
        "action": "dragged",
        "from": [fx, fy],
        "to": [tx, ty],
        "duration_ms": duration_ms,
    }, json_output)


# ── move ─────────────────────────────────────────────────────────────────────


@click.command()
@click.option("--to", "to_text", help="Target element text")
@click.option("--coords", nargs=2, type=int, metavar="X Y", help="Target X Y coordinates")
@click.option("--id", "element_id", help="Target element automation ID")
@click.option("--duration", type=float, default=0.0, help="Move duration (seconds)")
@click.option("--app", help="Application name")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle (HWND)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def move(to_text, coords, element_id, duration, app, window_title, hwnd,
         json_output):
    """Move the mouse cursor to a target element or coordinates.

    Examples:
      naturo move --coords 500 300
    """
    if not coords:
        _json_err("Specify --coords X Y", json_output)
        return

    backend = _get_backend()
    x, y = coords

    try:
        backend.move_mouse(x, y)
    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    _json_ok({"action": "moved", "x": x, "y": y}, json_output)


# ── paste ────────────────────────────────────────────────────────────────────


@click.command()
@click.argument("text", required=False)
@click.option("--file", "file_path", type=click.Path(exists=True), help="File to paste from")
@click.option("--restore", is_flag=True, default=True, help="Restore clipboard after paste")
@click.option("--app", help="Application name")
@click.option("--window-title", help="Window title pattern")
@click.option("--hwnd", type=int, help="Window handle (HWND)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def paste(text, file_path, restore, app, window_title, hwnd, json_output):
    """Set clipboard content and paste (Ctrl+V), then restore clipboard.

    TEXT is the string to paste. Or use --file to read from a file.

    Examples:
      naturo paste "Hello World"
      naturo paste --file mytext.txt
    """
    backend = _get_backend()

    if file_path:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    elif text:
        content = text
    else:
        _json_err("Specify TEXT or --file", json_output)
        return

    try:
        # Save existing clipboard
        old_clip = ""
        if restore:
            try:
                old_clip = backend.clipboard_get()
            except Exception:
                pass

        # Set new clipboard and paste
        backend.clipboard_set(content)
        backend.hotkey("ctrl", "v")

        # Restore clipboard
        if restore and old_clip:
            import time
            time.sleep(0.1)
            backend.clipboard_set(old_clip)

    except Exception as exc:
        _json_err(str(exc), json_output)
        return

    _json_ok({"action": "pasted", "length": len(content)}, json_output)
