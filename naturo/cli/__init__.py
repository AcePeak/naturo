"""Naturo CLI — Windows desktop automation, aligned with Peekaboo."""
import click
from naturo.version import __version__

from naturo.cli.core import capture, list_cmd, see, find_cmd, menu_inspect, learn, tools
from naturo.cli.interaction import (
    click_cmd, type_cmd, press, hotkey, scroll, drag, move, paste,
)
from naturo.cli.system import (
    app, window, menu, clipboard, dialog, open_cmd, taskbar, tray, desktop,
)
from naturo.cli.ai import agent, mcp
from naturo.cli.extensions import excel, java, sap, registry, service
from naturo.cli.snapshot import snapshot


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
main.add_command(tools)

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
main.add_command(window)
main.add_command(menu)
main.add_command(clipboard)
main.add_command(dialog)
main.add_command(open_cmd, "open")
main.add_command(taskbar)
main.add_command(tray)
main.add_command(desktop)

# ── AI ──────────────────────────────────────────
main.add_command(agent)
main.add_command(mcp)

# ── Windows Extensions ─────────────────────────
main.add_command(excel)
main.add_command(java)
main.add_command(sap)
main.add_command(registry)
main.add_command(service)

# ── Snapshot ────────────────────────────────────
main.add_command(snapshot)
