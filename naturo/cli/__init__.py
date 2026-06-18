"""Naturo CLI — Windows desktop automation, aligned with Peekaboo."""
from __future__ import annotations

import json
import os
import sys

# Ensure UTF-8 mode on Windows to handle Unicode arguments and output correctly.
# This is equivalent to setting PYTHONUTF8=1 but applies programmatically.
if sys.platform == "win32" and not os.environ.get("PYTHONUTF8"):
    os.environ["PYTHONUTF8"] = "1"
    # Reconfigure stdout/stderr to UTF-8 if they're still using the default encoding
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass  # Best-effort: logging not yet configured at import time
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass  # Best-effort: logging not yet configured at import time

import click
from naturo.version import __version__
from naturo.cli.error_helpers import json_error
from naturo.cli.fuzzy_group import FuzzyGroup

from naturo.cli.core import capture, list_cmd, see, find_cmd, menu_inspect, highlight
from naturo.cli.values import get_cmd, set_cmd
from naturo.cli.interaction import (
    click_cmd, type_cmd, press, hotkey, scroll, drag, move,
)
from naturo.cli._app_group import app
from naturo.cli.system import clipboard, dialog, taskbar, tray, desktop
from naturo.cli.snapshot import snapshot
from naturo.cli.wait_cmd import wait
from naturo.cli.app_cmd import (
    app_launch, app_quit, app_relaunch, app_list, app_find, app_hide, app_unhide, app_switch, app_inspect,
    app_focus, app_close, app_minimize, app_maximize, app_restore, app_move, app_windows,
)
from naturo.cli.window_cmd import window
from naturo.cli.diff_cmd import diff
from naturo.cli.ai import mcp
from naturo.cli.extensions import excel
from naturo.cli.browser_cmd import browser

from naturo.cli.selector_cmd import selector
from naturo.cli.visual_cmd import visual
from naturo.cli.recording_cmd import record
from naturo.cli.config_cmd import config_cmd as _config_cmd_group


# Accept ``-h`` as the POSIX synonym for ``--help`` (#899). Declaring it on the
# root group lets child contexts inherit ``help_option_names`` *when they are
# reached through the root*. That inheritance alone is not enough, though:
# Click (>=8.1.8) lazily builds the help option from the first context a command
# is invoked under and then caches it on ``Command._help_option`` forever. If a
# command is ever first invoked through a parentless context — e.g. a test doing
# ``CliRunner().invoke(subcommand, ["--help"])`` — that context falls back to the
# default ``["--help"]`` and the command caches a help option without ``-h``.
# To make ``-h`` reliable on every command regardless of invocation order, we
# also stamp ``help_option_names`` onto each command's own ``context_settings``
# (see ``_apply_short_help``), so even a parentless context resolves ``-h``.
HELP_OPTION_NAMES = ["-h", "--help"]
CONTEXT_SETTINGS = {"help_option_names": HELP_OPTION_NAMES}


def _patch_json_flag(cmd) -> None:
    """Patch --json/-j flag on a Click command to inherit from parent ctx.obj['json'].

    Replaces the ``json_output`` flag's callback so that when the flag is not
    explicitly passed on the command line, it checks ``ctx.obj["json"]``
    (set by the root ``naturo --json``).
    """
    for param in cmd.params:
        if param.name == "json_output" and isinstance(param, click.Option):
            original_callback = param.callback

            def _json_callback(ctx, _param, value, _orig=original_callback):
                # If the user explicitly passed --json on the subcommand, use it
                if value:
                    return True if _orig is None else _orig(ctx, _param, True)
                # Otherwise check parent context chain for global --json
                check = ctx
                while check is not None:
                    obj = getattr(check, "obj", None)
                    if obj and obj.get("json"):
                        return True if _orig is None else _orig(ctx, _param, True)
                    check = check.parent
                return False if _orig is None else _orig(ctx, _param, False)

            param.callback = _json_callback
            break


def _apply_short_help(cmd: click.Command) -> None:
    """Ensure ``-h`` works as ``--help`` on ``cmd`` regardless of invocation order.

    Stamps ``help_option_names`` onto the command's own ``context_settings`` so
    that even a parentless context (which would otherwise default to
    ``["--help"]``) resolves ``-h``, and clears any help option Click may have
    already cached so it is rebuilt with the new names (#899).
    """
    cmd.context_settings["help_option_names"] = list(HELP_OPTION_NAMES)
    # Click caches the help option on first use; drop the cache so the next
    # invocation rebuilds it from the names above. ``_help_option`` is absent on
    # older Click versions that do not cache, so guard with ``hasattr``.
    if hasattr(cmd, "_help_option"):
        cmd._help_option = None


def _patch_all_commands(group: click.Command) -> None:
    """Recursively patch all commands under a group for --json and ``-h`` support."""
    if isinstance(group, click.Group):
        for cmd in group.commands.values():
            _patch_all_commands(cmd)
    _patch_json_flag(group)
    _apply_short_help(group)


@click.group(cls=FuzzyGroup, context_settings=CONTEXT_SETTINGS)
@click.version_option(__version__, prog_name="naturo")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.option("--verbose", "-v", is_flag=True, help="Verbose logging")
@click.option(
    "--log-level",
    type=click.Choice(
        ["trace", "debug", "info", "warning", "error"], case_sensitive=False
    ),
    default="info",
    help="Log level",
)
@click.pass_context
def main(ctx, json_output, verbose, log_level) -> None:
    """Naturo — Windows desktop automation engine.

    See, click, type, automate. Built for AI agents.
    Peekaboo-compatible command structure with Windows extensions.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output
    ctx.obj["verbose"] = verbose
    ctx.obj["log_level"] = log_level

    # (#783) Configure logging: suppress all output in JSON mode to prevent
    # log messages from polluting the JSON stream on stderr.
    import logging
    if json_output:
        root = logging.getLogger()
        root.handlers.clear()
        root.addHandler(logging.NullHandler())
    elif verbose or log_level != "info":
        level = logging.DEBUG if verbose else getattr(logging, log_level.upper())
        logging.basicConfig(level=level, stream=sys.stderr, format="%(levelname)s: %(message)s")


# ── Core ────────────────────────────────────────
main.add_command(capture)
main.add_command(list_cmd, "list")
main.add_command(see)
main.add_command(find_cmd, "find")
main.add_command(get_cmd, "get")
main.add_command(set_cmd, "set")
main.add_command(menu_inspect, "menu-inspect")
main.add_command(highlight)

# ── Interaction ─────────────────────────────────
main.add_command(click_cmd, "click")
main.add_command(type_cmd, "type")
main.add_command(press)
main.add_command(hotkey)
main.add_command(scroll)
main.add_command(drag)
main.add_command(move)

# ── System ──────────────────────────────────────
main.add_command(app)
main.add_command(clipboard)
main.add_command(dialog)
main.add_command(taskbar)
main.add_command(tray)
main.add_command(desktop)

# ── Window Management ───────────────────────────
main.add_command(window)

# ── Snapshot ────────────────────────────────────
main.add_command(snapshot)

# ── Phase 3: Stabilize ─────────────────────────
main.add_command(wait)
main.add_command(diff)

# ── Phase 4: AI Integration ─────────────────────
main.add_command(mcp)

# ── Phase 5C: Enterprise Features ──────────────
main.add_command(excel)

# ── Browser Automation ─────────────────────────
main.add_command(browser)



# ── Help alias ─────────────────────────────────
# Users naturally try `naturo help` (like git/docker). Redirect to --help.
@main.command("help", hidden=True)
@click.pass_context
def help_cmd(ctx) -> None:
    """Show help information (alias for --help)."""
    click.echo(ctx.parent.get_help())


# ── Config / Credentials ────────────────────────
main.add_command(selector)
main.add_command(visual)
main.add_command(record)
main.add_command(_config_cmd_group, "config")

# Replace stub app subcommands with working implementations
app.add_command(app_launch, "launch")
app.add_command(app_quit, "quit")
app.add_command(app_relaunch, "relaunch")
app.add_command(app_list, "list")
app.add_command(app_find, "find")
app.add_command(app_inspect, "inspect")

# Window operations unified under app (#170)
app.add_command(app_focus, "focus")
app.add_command(app_close, "close")
app.add_command(app_minimize, "minimize")
app.add_command(app_maximize, "maximize")
app.add_command(app_restore, "restore")
app.add_command(app_move, "move")
app.add_command(app_windows, "windows")

# Legacy aliases (hidden from help but still work)
app.add_command(app_switch, "switch")  # alias for focus
app.add_command(app_hide, "hide")      # alias for minimize
app.add_command(app_unhide, "unhide")  # alias for restore


# ── Patch all commands to propagate global --json to subcommands ─────────────
_patch_all_commands(main)


# ── Console-script wrapper: honour global -j/--json on Click's eager paths ───
# Click resolves --version/--help and reports unknown commands *before* any
# naturo command code runs, emitting plain text and (for unknown commands)
# exit code 2. That breaks the global JSON contract for callers that pipe
# ``naturo -j --version`` / ``-j --help`` / ``-j <unknown>`` into a JSON parser.
# ``run`` (the console-script entry point) wraps the group to close that gap
# while leaving every other code path byte-for-byte identical to plain Click.
# See #874 (top-level twin of the subcommand-level #872).

# The only root-group option that consumes a following token as its value.
_GLOBAL_VALUE_OPTIONS = {"--log-level"}


def _wants_global_json(argv: list[str]) -> bool:
    """Return True if a global ``-j``/``--json`` precedes any subcommand.

    Scans the leading option tokens only: a ``-j`` placed *after* the
    subcommand name is a subcommand-level flag, not the global one.

    Args:
        argv: CLI arguments excluding the program name.

    Returns:
        True when global JSON output was requested, otherwise False.
    """
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in ("-j", "--json"):
            return True
        # Combined short-flag cluster, e.g. "-vj".
        if token.startswith("-") and not token.startswith("--") and "j" in token[1:]:
            return True
        if token in _GLOBAL_VALUE_OPTIONS:
            index += 2  # skip the option and its value
            continue
        if token.startswith("-"):
            index += 1
            continue
        break  # first positional token is the subcommand
    return False


def _wants_json(argv: list[str]) -> bool:
    """Return True if ``-j``/``--json`` appears anywhere on the command line.

    Unlike :func:`_wants_global_json` (which only inspects the leading global
    options), this scans the full token list so a subcommand-level ``-j`` placed
    *after* the command name — e.g. ``naturo see --hwnd abc -j`` — is detected
    too. Used to decide whether a parse-time usage error should be rendered as a
    JSON envelope (#872). Tokens after a literal ``--`` are positional and never
    treated as flags.

    Args:
        argv: CLI arguments excluding the program name.

    Returns:
        True when JSON output was requested anywhere, otherwise False.
    """
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--":
            break  # everything after -- is a positional argument
        if token in ("-j", "--json"):
            return True
        # Combined short-flag cluster, e.g. "-vj".
        if token.startswith("-") and not token.startswith("--") and "j" in token[1:]:
            return True
        if token in _GLOBAL_VALUE_OPTIONS:
            index += 2  # skip the option and its value
            continue
        index += 1
    return False


def _first_command_token(argv: list[str]) -> str | None:
    """Return the first positional token (the subcommand), or None.

    Args:
        argv: CLI arguments excluding the program name.

    Returns:
        The subcommand name, or None when only global options were given.
    """
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in _GLOBAL_VALUE_OPTIONS:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token
    return None


def _root_help_json() -> str:
    """Build the structured JSON envelope for root-level ``--help``.

    Returns:
        A JSON string with ``success`` and a ``help`` object containing the
        usage line, visible subcommands, and global options.
    """
    ctx = click.Context(main, info_name="naturo")
    commands = []
    for name in main.list_commands(ctx):
        cmd = main.get_command(ctx, name)
        if cmd is None or cmd.hidden:
            continue
        commands.append({"name": name, "help": cmd.get_short_help_str()})

    options = []
    for param in main.get_params(ctx):
        if not isinstance(param, click.Option):
            continue
        record = param.get_help_record(ctx)
        if record is not None:
            options.append({"name": record[0], "help": record[1]})

    usage = "naturo " + " ".join(main.collect_usage_pieces(ctx))
    return json.dumps(
        {
            "success": True,
            "help": {"usage": usage, "commands": commands, "options": options},
        }
    )


def _emit_usage_error_json(exc: click.UsageError) -> None:
    """Emit a JSON error envelope for any parse-time usage error and exit 1.

    Handles both root-group errors (#874) and subcommand errors (#872): every
    Click parse failure class — unknown option, unknown command, missing
    argument, and invalid option/argument values (bad int/float/choice) — is
    mapped onto the standard ``{success: false, error: {...}}`` envelope. The
    ``--help`` hint targets the failing command so the suggested action is
    actionable for nested commands (e.g. ``naturo clipboard set``).

    Args:
        exc: The Click usage error raised during argument parsing.
    """
    message = exc.format_message()
    # ``exc.ctx`` is the context of the command that failed to parse; its
    # ``command_path`` is "naturo" for the root group or e.g. "naturo clipboard
    # set" for a nested subcommand.
    help_target = "naturo" if exc.ctx is None else exc.ctx.command_path
    if isinstance(exc, click.NoSuchOption):
        code = "UNKNOWN_OPTION"
        action = f"Run '{help_target} --help' to see the available options."
    elif message.startswith("No such command"):
        code = "UNKNOWN_COMMAND"
        action = f"Run '{help_target} --help' for the command list."
    else:
        code = "INVALID_INPUT"
        action = f"Run '{help_target} --help' for usage."
    click.echo(json_error(code, message, suggested_action=action))
    # Contract exit code is 1 (runtime error), not Click's UsageError 2 — same
    # axis as #866/#872.
    sys.exit(1)


def run() -> None:
    """Console-script entry point wrapping the Click group (#874).

    Preserves the global ``-j/--json`` contract for code paths Click would
    otherwise emit as plain text — the eager ``--version`` / ``--help``
    handlers and root-level usage errors — while delegating every other
    invocation to standard Click dispatch unchanged.
    """
    argv = sys.argv[1:]
    json_mode = _wants_global_json(argv)
    # Usage errors honour ``-j`` placed anywhere (global or subcommand-level),
    # since a parse failure can occur before Click binds the flag (#872).
    json_usage = _wants_json(argv)

    # --version/--help are eager: Click runs and prints them before command
    # dispatch, so intercept them here when global JSON is requested and no
    # subcommand was given (subcommand-level --help stays Click's job).
    if json_mode and _first_command_token(argv) is None:
        if "--version" in argv:
            click.echo(json.dumps({"success": True, "version": __version__}))
            sys.exit(0)
        if "--help" in argv or "-h" in argv:
            click.echo(_root_help_json())
            sys.exit(0)

    try:
        # standalone_mode=False so usage errors propagate here instead of being
        # printed by Click; it also makes eager handlers (--version/--help on a
        # subcommand) and ctx.exit() *return* their exit code rather than
        # raising SystemExit, so propagate that explicitly.
        result = main.main(args=argv, prog_name="naturo", standalone_mode=False)
        sys.exit(result if isinstance(result, int) else 0)
    except click.UsageError as exc:
        # Every parse-time usage error — root group (#874) or subcommand
        # (#872) — is wrapped in the JSON envelope when JSON was requested.
        # Runtime guards (e.g. NO_DESKTOP_SESSION) emit their own envelope and
        # sys.exit before reaching here, so this only catches parse failures.
        if json_usage:
            _emit_usage_error_json(exc)
        exc.show()
        sys.exit(exc.exit_code)
    except click.Abort:
        click.echo("Aborted!", err=True)
        sys.exit(1)
    except click.ClickException as exc:
        exc.show()
        sys.exit(exc.exit_code)
