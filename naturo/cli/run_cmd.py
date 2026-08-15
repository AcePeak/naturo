"""``naturo run`` — execute a user Python script with the bundled runtime (#42).

Runs ``naturo run script.py`` or ``naturo run -c "code"`` under the interpreter
chosen by the #41 resolver (system Python preferred, embedded runtime as
fallback), with the #924 naturo SDK importable inside the script — so a user
script can simply ``from naturo import click, see, type`` and automate.

The heavy lifting (subprocess, timeout-kill, error classification, exit-code
propagation) lives in :mod:`naturo.scripting`; this module is the thin Click
wrapper that parses options and renders the result.
"""
from __future__ import annotations

import shlex
from typing import Optional

import click

from naturo.cli._jsonio import json_dumps
from naturo.cli.error_helpers import emit_usage_error
from naturo.scripting import RunResult, run_script


def _emit(result: RunResult, json_output: bool) -> None:
    """Render a :class:`RunResult` to stdout/stderr (text or JSON).

    Text mode forwards the script's own stdout/stderr verbatim (so a traceback
    is still visible) and, on a classified fault, appends a concise
    ``naturo run: <message>`` summary line to stderr. JSON mode emits a single
    envelope carrying the exit code, captured streams, and any fault.
    """
    if json_output:
        payload: dict[str, object] = {
            "success": result.error_kind is None and result.exit_code == 0,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        if result.error_kind:
            payload["error"] = {"kind": result.error_kind, "message": result.message}
        click.echo(json_dumps(payload))
        return

    if result.stdout:
        click.echo(result.stdout, nl=False)
    if result.stderr:
        click.echo(result.stderr, nl=False, err=True)
    if result.error_kind and result.message:
        click.secho(f"naturo run: {result.message}", fg="red", err=True)


@click.command("run")
@click.argument("script", required=False)
@click.option("-c", "--code", "code", default=None, help="Execute an inline code string instead of a file.")
@click.option(
    "--args",
    "args_str",
    default=None,
    help="Arguments passed to the script as sys.argv[1:] (shell-quoted, e.g. --args \"a b c\").",
)
@click.option("--timeout", type=float, default=None, help="Kill the script after N seconds.")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def run_cmd(
    ctx: click.Context,
    script: Optional[str],
    code: Optional[str],
    args_str: Optional[str],
    timeout: Optional[float],
    json_output: bool,
) -> None:
    """Execute a Python script (or -c code) with the naturo SDK importable.

    The script runs in a subprocess under the resolver's interpreter (system
    Python preferred, embedded runtime fallback). ``import naturo`` works inside
    it, so a script can drive the desktop with the #924 SDK. The script's own
    exit code is propagated; --timeout kills a runaway run.

    \b
    Examples:
      naturo run automate.py
      naturo run automate.py --args "input.csv --verbose"
      naturo run -c "from naturo import windows; print(len(windows()))"
      naturo run long_task.py --timeout 30
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    if script and code:
        emit_usage_error("Pass either a SCRIPT path or -c/--code, not both.", json_output)
    if not script and not code:
        emit_usage_error("Provide a SCRIPT path or -c/--code to run.", json_output)
    if timeout is not None and timeout <= 0:
        emit_usage_error("--timeout must be a positive number of seconds.", json_output)

    forwarded = shlex.split(args_str) if args_str else []

    result = run_script(script=script, code=code, args=forwarded, timeout=timeout)
    _emit(result, json_output)
    ctx.exit(result.exit_code)
