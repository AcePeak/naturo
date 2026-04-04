"""App command group — Click group stub for ``naturo app`` subcommands.

The actual subcommand implementations live in ``naturo.cli.app_cmd``.
This module only defines the top-level group so that ``cli/__init__.py``
can register subcommands onto it.
"""
import click
from naturo.cli.fuzzy_group import FuzzyGroup


@click.group(cls=FuzzyGroup)
def app() -> None:
    """Manage applications and windows: launch, quit, focus, close, minimize, maximize, restore, move, and more."""
    pass


@app.command(hidden=True)
@click.argument("name")
@click.option("--args", multiple=True, help="Launch arguments")
@click.option("--wait", is_flag=True, help="Wait for app to start")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def launch(name, args, wait, json_output) -> None:
    """Launch an application by name or path."""
    click.echo("Not implemented yet. See 'naturo app --help' for available commands.")


@app.command(hidden=True)
@click.argument("name")
@click.option("--pid", type=int, help="Process ID")
@click.option("--force", is_flag=True, help="Force kill")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def quit(name, pid, force, json_output) -> None:
    """Quit an application gracefully (or force kill)."""
    click.echo("Not implemented yet. See 'naturo app --help' for available commands.")


@app.command(hidden=True)
@click.argument("name")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def relaunch(name, json_output) -> None:
    """Quit and relaunch an application."""
    click.echo("Not implemented yet. See 'naturo app --help' for available commands.")


@app.command(name="list", hidden=True)
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def app_list(json_output) -> None:
    """List running applications."""
    click.echo("Not implemented yet. See 'naturo app --help' for available commands.")
