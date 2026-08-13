"""``naturo hook`` — install, list, remove, and monitor Win32 API hooks (#40).

In-process Win32 API function hooking backed by the vendored MinHook engine in
``naturo_core``. Hooks are installed on a curated set of resolvable exported
APIs (``naturo hook`` targets the current process); each intercepted call is
recorded in a thread-safe log that ``naturo hook monitor`` drains.

    naturo hook install user32 MessageBoxW           # log every MessageBoxW
    naturo hook install kernel32 CreateFileW --action block
    naturo hook list                                 # active hooks
    naturo hook monitor                              # drain the call log
    naturo hook remove user32 MessageBoxW

Security: hooking intercepts real application calls. The ``block`` action makes
a hooked API return a failure sentinel instead of running — use it deliberately.
Cross-process injection (loading naturo into another process) is a separate,
administrator-only operation exposed through :mod:`naturo.hooks.injector`.
"""
from __future__ import annotations

import click

from naturo.cli._jsonio import json_dumps
from naturo.cli.error_helpers import emit_error, emit_exception_error
from naturo.cli.fuzzy_group import FuzzyGroup


def _manager():
    """Construct a :class:`naturo.hooks.manager.HookManager` (import kept lazy)."""
    from naturo.hooks.manager import HookManager

    return HookManager()


@click.group(cls=FuzzyGroup)
def hook() -> None:
    """Install and monitor Win32 API hooks (in-process, MinHook-backed).

    \b
    Examples:
        naturo hook install user32 MessageBoxW
        naturo hook install kernel32 CreateFileW --action block
        naturo hook list
        naturo hook monitor
        naturo hook remove user32 MessageBoxW
    """
    pass


@hook.command("install")
@click.argument("module")
@click.argument("function")
@click.option(
    "--action",
    type=click.Choice(["log", "block"]),
    default="log",
    help="log = record and forward; block = record and return a sentinel.",
)
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def hook_install(module: str, function: str, action: str, json_output: bool) -> None:
    """Install (or re-arm) a hook on MODULE!FUNCTION.

    \b
    Examples:
        naturo hook install user32 MessageBoxW
        naturo hook install kernel32 CreateFileW --action block
    """
    from naturo.hooks.manager import HookError

    try:
        info = _manager().install(module, function, action)
    except HookError as exc:
        emit_error("INVALID_INPUT", str(exc), json_output)
        return
    except Exception as exc:  # native/bridge failure
        emit_exception_error(exc, json_output, fallback_code="HOOK_ERROR")
        return

    if json_output:
        click.echo(json_dumps({"success": True, "action": "hook_install", **info}))
    else:
        click.echo(f"Hooked {info['module']}!{info['function']} (action: {info['action']})")


@hook.command("list")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def hook_list(json_output: bool) -> None:
    """List the currently installed hooks.

    \b
    Examples:
        naturo hook list
        naturo hook list --json
    """
    try:
        hooks = _manager().list()
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="HOOK_ERROR")
        return

    if json_output:
        click.echo(json_dumps({"success": True, "action": "hook_list", "hooks": hooks, "count": len(hooks)}))
    else:
        if not hooks:
            click.echo("No hooks installed.")
            return
        for h in hooks:
            click.echo(f"{h['module']}!{h['function']}  action={h['action']}  calls={h['call_count']}")


@hook.command("remove")
@click.argument("module")
@click.argument("function")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def hook_remove(module: str, function: str, json_output: bool) -> None:
    """Remove the hook on MODULE!FUNCTION.

    \b
    Examples:
        naturo hook remove user32 MessageBoxW
    """
    from naturo.hooks.manager import HookError

    try:
        removed = _manager().remove(module, function)
    except HookError as exc:
        emit_error("INVALID_INPUT", str(exc), json_output)
        return
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="HOOK_ERROR")
        return

    if json_output:
        click.echo(json_dumps({
            "success": True, "action": "hook_remove",
            "module": module, "function": function, "removed": removed,
        }))
    else:
        if removed:
            click.echo(f"Removed hook {module}!{function}")
        else:
            click.echo(f"No hook installed on {module}!{function}")


@hook.command("monitor")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def hook_monitor(json_output: bool) -> None:
    """Drain and print the monitored-call log (clears the buffer).

    Returns every intercepted call recorded since the last drain, oldest-first.

    \b
    Examples:
        naturo hook monitor
        naturo hook monitor --json
    """
    try:
        events = _manager().monitor()
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="HOOK_ERROR")
        return

    if json_output:
        click.echo(json_dumps({"success": True, "action": "hook_monitor", "events": events, "count": len(events)}))
    else:
        if not events:
            click.echo("No calls recorded.")
            return
        for e in events:
            click.echo(f"#{e['seq']} {e['module']}!{e['function']}  [{e['action']}]  {e['detail']}")
