"""Naturo CLI — Windows desktop automation, aligned with Peekaboo."""
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
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

import click
from naturo.version import __version__

from naturo.cli.core import capture, list_cmd, see, find_cmd, menu_inspect, learn
from naturo.cli.interaction import (
    click_cmd, type_cmd, press, hotkey, scroll, drag, move, paste,
)
from naturo.cli.system import app, clipboard
from naturo.cli.snapshot import snapshot
from naturo.cli.wait_cmd import wait
from naturo.cli.app_cmd import app_launch, app_quit, app_relaunch, app_list, app_find, app_hide, app_unhide, app_switch
from naturo.cli.window_cmd import window
from naturo.cli.diff_cmd import diff
from naturo.cli.ai import mcp, describe, agent


@click.group()
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
def main(ctx, json_output, verbose, log_level):
    """Naturo — Windows desktop automation engine.

    See, click, type, automate. Built for AI agents.
    Peekaboo-compatible command structure with Windows extensions.
    """
    ctx.ensure_object(dict)
    ctx.obj["json"] = json_output
    ctx.obj["verbose"] = verbose
    ctx.obj["log_level"] = log_level


# ── Core ────────────────────────────────────────
main.add_command(capture)
main.add_command(list_cmd, "list")
main.add_command(see)
main.add_command(find_cmd, "find")
main.add_command(menu_inspect, "menu-inspect")
main.add_command(learn)

# ── Interaction ─────────────────────────────────
main.add_command(click_cmd, "click")
main.add_command(type_cmd, "type")
main.add_command(press)
main.add_command(hotkey)
main.add_command(scroll)
main.add_command(drag)
main.add_command(move)
main.add_command(paste)

# ── System ──────────────────────────────────────
main.add_command(app)
main.add_command(clipboard)

# ── Window Management ───────────────────────────
main.add_command(window)

# ── Snapshot ────────────────────────────────────
main.add_command(snapshot)

# ── Phase 3: Stabilize ─────────────────────────
main.add_command(wait)
main.add_command(diff)

# ── Phase 4: AI Integration ─────────────────────
main.add_command(agent)
main.add_command(describe)
main.add_command(mcp)

# Replace stub app subcommands with working implementations
app.add_command(app_launch, "launch")
app.add_command(app_quit, "quit")
app.add_command(app_relaunch, "relaunch")
app.add_command(app_list, "list")
app.add_command(app_find, "find")
app.add_command(app_hide, "hide")
app.add_command(app_unhide, "unhide")
app.add_command(app_switch, "switch")
