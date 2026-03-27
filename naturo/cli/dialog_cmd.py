"""Dialog CLI commands — detect and interact with system dialogs.

Phase 4.5.1 + 4.5.2: Dialog Detection & Interaction.

Provides commands to detect active dialog windows (message boxes, file pickers,
confirmations) and interact with them (accept, dismiss, click buttons, type text).

Examples:
    naturo dialog detect                     # List active dialogs
    naturo dialog detect --app notepad       # Filter by app
    naturo dialog accept                     # Click OK/Yes/Open
    naturo dialog dismiss                    # Click Cancel/No/Close
    naturo dialog click-button "Save"        # Click specific button
    naturo dialog type "hello.txt"           # Type in input field
    naturo dialog type "hello.txt" --accept  # Type then click OK
"""

from __future__ import annotations

import json as _json

import click

from naturo.cli.error_helpers import emit_error, emit_exception_error
from naturo.cli.fuzzy_group import FuzzyGroup


@click.group(cls=FuzzyGroup)
def dialog():
    """Detect and interact with system dialogs.

    Handles message boxes, file pickers, confirmation prompts, and other
    modal dialog windows. Essential for AI agent automation when dialogs
    block the main workflow.

    \b
    Examples:
        naturo dialog detect                   # List active dialogs
        naturo dialog detect --app notepad     # Filter by app
        naturo dialog accept                   # Click OK/Yes/Open
        naturo dialog dismiss                  # Click Cancel/No/Close
        naturo dialog click-button "Save"      # Click a specific button
        naturo dialog type "hello.txt"         # Type into dialog input
    """
    pass


@dialog.command()
@click.option("--app", help="Filter by owner application name")
@click.option("--hwnd", type=int, help="Filter by dialog window handle")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def detect(app, hwnd, json_output):
    """Detect active dialog windows.

    Scans for system dialogs including message boxes, file pickers,
    confirmation prompts, and application-specific modal dialogs.

    Returns dialog type, title, message, available buttons, and
    whether an input field is present.

    \b
    Examples:
        naturo dialog detect                   # List all dialogs
        naturo dialog detect --app notepad     # Filter by app
        naturo dialog detect --json            # JSON output
    """
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    try:
        backend = get_backend()
        dialogs = backend.detect_dialogs(app=app, hwnd=hwnd)

        if json_output:
            result = {
                "success": True,
                "dialogs": [d.to_dict() for d in dialogs],
                "count": len(dialogs),
            }
            click.echo(_json.dumps(result))
        else:
            if not dialogs:
                click.echo("No dialogs detected.")
            else:
                for i, d in enumerate(dialogs):
                    if i > 0:
                        click.echo()
                    click.echo(f"Dialog: {d.title}")
                    click.echo(f"  Type: {d.dialog_type.value}")
                    click.echo(f"  HWND: {d.hwnd}")
                    if d.message:
                        click.echo(f"  Message: {d.message}")
                    if d.buttons:
                        btn_names = ", ".join(b.name for b in d.buttons)
                        click.echo(f"  Buttons: {btn_names}")
                    if d.has_input:
                        click.echo(f"  Input: {d.input_value!r}")
                    if d.owner_app:
                        click.echo(f"  Owner: {d.owner_app}")

    except NaturoError as e:
        emit_exception_error(e, json_output)
    except Exception as e:
        emit_exception_error(e, json_output, fallback_code="UNKNOWN_ERROR")


@dialog.command()
@click.option("--app", help="Owner application name filter")
@click.option("--hwnd", type=int, help="Specific dialog window handle")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def accept(app, hwnd, json_output):
    """Accept (confirm) the active dialog.

    Clicks the first accept-type button found: OK, Yes, Open, Save,
    Continue, Apply, Print, 确定, 是, etc.

    \b
    Examples:
        naturo dialog accept                   # Accept first dialog
        naturo dialog accept --app notepad     # Accept notepad's dialog
        naturo dialog accept --json            # JSON output
    """
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError
    from naturo.dialog import _ACCEPT_BUTTONS

    try:
        backend = get_backend()
        dialogs = backend.detect_dialogs(app=app, hwnd=hwnd)
        if not dialogs:
            emit_error("DIALOG_NOT_FOUND", "No dialog detected", json_output)

        target_dialog = dialogs[0]
        if hwnd:
            target_dialog = next((d for d in dialogs if d.hwnd == hwnd), dialogs[0])

        # Find the accept button
        accept_btn = None
        for btn in target_dialog.buttons:
            if btn.name.lower() in _ACCEPT_BUTTONS or btn.is_default:
                accept_btn = btn
                break

        if not accept_btn:
            available = ", ".join(b.name for b in target_dialog.buttons)
            emit_error(
                "ELEMENT_NOT_FOUND",
                f"No accept button found in dialog. Available: [{available}]",
                json_output,
            )

        backend.click(x=accept_btn.x, y=accept_btn.y)

        if json_output:
            click.echo(_json.dumps({
                "success": True,
                "dialog_title": target_dialog.title,
                "button_clicked": accept_btn.name,
                "dialog_hwnd": target_dialog.hwnd,
            }))
        else:
            click.echo(f"Accepted dialog '{target_dialog.title}' (clicked '{accept_btn.name}')")

    except NaturoError as e:
        emit_exception_error(e, json_output)
    except SystemExit:
        raise
    except Exception as e:
        emit_exception_error(e, json_output, fallback_code="UNKNOWN_ERROR")


@dialog.command()
@click.option("--app", help="Owner application name filter")
@click.option("--hwnd", type=int, help="Specific dialog window handle")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def dismiss(app, hwnd, json_output):
    """Dismiss (cancel) the active dialog.

    Clicks the first dismiss-type button found: Cancel, No, Close,
    Abort, 取消, 否, etc.

    \b
    Examples:
        naturo dialog dismiss                  # Dismiss first dialog
        naturo dialog dismiss --app notepad    # Dismiss notepad's dialog
        naturo dialog dismiss --json           # JSON output
    """
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError
    from naturo.dialog import _DISMISS_BUTTONS

    try:
        backend = get_backend()
        dialogs = backend.detect_dialogs(app=app, hwnd=hwnd)
        if not dialogs:
            emit_error("DIALOG_NOT_FOUND", "No dialog detected", json_output)

        target_dialog = dialogs[0]
        if hwnd:
            target_dialog = next((d for d in dialogs if d.hwnd == hwnd), dialogs[0])

        # Find the dismiss button
        dismiss_btn = None
        for btn in target_dialog.buttons:
            if btn.name.lower() in _DISMISS_BUTTONS or btn.is_cancel:
                dismiss_btn = btn
                break

        if not dismiss_btn:
            available = ", ".join(b.name for b in target_dialog.buttons)
            emit_error(
                "ELEMENT_NOT_FOUND",
                f"No dismiss button found in dialog. Available: [{available}]",
                json_output,
            )

        backend.click(x=dismiss_btn.x, y=dismiss_btn.y)

        if json_output:
            click.echo(_json.dumps({
                "success": True,
                "dialog_title": target_dialog.title,
                "button_clicked": dismiss_btn.name,
                "dialog_hwnd": target_dialog.hwnd,
            }))
        else:
            click.echo(f"Dismissed dialog '{target_dialog.title}' (clicked '{dismiss_btn.name}')")

    except NaturoError as e:
        emit_exception_error(e, json_output)
    except SystemExit:
        raise
    except Exception as e:
        emit_exception_error(e, json_output, fallback_code="UNKNOWN_ERROR")


@dialog.command("click-button")
@click.argument("button")
@click.option("--app", help="Owner application name filter")
@click.option("--hwnd", type=int, help="Specific dialog window handle")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def click_button(button, app, hwnd, json_output):
    """Click a specific button in the active dialog.

    Finds a button by name (case-insensitive, supports partial match)
    and clicks it.

    \b
    Examples:
        naturo dialog click-button "Save"         # Click Save
        naturo dialog click-button "Don't Save"   # Click Don't Save
        naturo dialog click-button "Retry"         # Click Retry
    """
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError

    if not button.strip():
        emit_error("INVALID_INPUT", "Button name cannot be empty", json_output)

    try:
        backend = get_backend()
        result = backend.dialog_click_button(button=button, app=app, hwnd=hwnd)

        if json_output:
            click.echo(_json.dumps({"success": True, **result}))
        else:
            click.echo(
                f"Clicked '{result['button_clicked']}' in dialog '{result['dialog_title']}'"
            )

    except NaturoError as e:
        emit_exception_error(e, json_output)
    except SystemExit:
        raise
    except Exception as e:
        emit_exception_error(e, json_output, fallback_code="UNKNOWN_ERROR")


@dialog.command("type")
@click.argument("text")
@click.option("--accept", "do_accept", is_flag=True,
              help="Click OK/Accept after typing")
@click.option("--app", help="Owner application name filter")
@click.option("--hwnd", type=int, help="Specific dialog window handle")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def dialog_type(text, do_accept, app, hwnd, json_output):
    """Type text into a dialog's input field.

    Finds the dialog's input/edit control, clears it, and types
    the provided text. With --accept, also clicks the OK button.

    \b
    Examples:
        naturo dialog type "hello.txt"            # Type filename
        naturo dialog type "hello.txt" --accept   # Type then click OK
        naturo dialog type "C:\\Users" --app notepad
    """
    from naturo.backends.base import get_backend
    from naturo.errors import NaturoError
    from naturo.dialog import _ACCEPT_BUTTONS

    if not text:
        emit_error("INVALID_INPUT", "Text cannot be empty", json_output)

    try:
        backend = get_backend()
        result = backend.dialog_set_input(text=text, app=app, hwnd=hwnd)

        accepted_button = None
        if do_accept:
            dialogs = backend.detect_dialogs(app=app, hwnd=hwnd)
            if dialogs:
                for btn in dialogs[0].buttons:
                    if btn.name.lower() in _ACCEPT_BUTTONS or btn.is_default:
                        backend.click(x=btn.x, y=btn.y)
                        accepted_button = btn.name
                        break

        if json_output:
            out = {"success": True, **result}
            if accepted_button:
                out["accepted_with"] = accepted_button
            click.echo(_json.dumps(out))
        else:
            msg = f"Typed '{text}' in dialog '{result['dialog_title']}'"
            if accepted_button:
                msg += f" (accepted with '{accepted_button}')"
            click.echo(msg)

    except NaturoError as e:
        emit_exception_error(e, json_output)
    except SystemExit:
        raise
    except Exception as e:
        emit_exception_error(e, json_output, fallback_code="UNKNOWN_ERROR")
