"""Tools command — list available automation tools and backends."""
from __future__ import annotations

import click

import naturo.cli.core._common as _common


@click.command(hidden=True)
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def tools(json_output) -> None:
    """List available automation tools and backends.

    Shows which native backends are available (UIA, MSAA, Java Bridge, etc.).
    """
    msg = "Tools listing is not implemented yet \u2014 coming in a future release."
    if json_output:
        click.echo(_common._json_error_str("NOT_IMPLEMENTED", msg))
    else:
        click.echo(f"Error: {msg}", err=True)
    raise SystemExit(1)
