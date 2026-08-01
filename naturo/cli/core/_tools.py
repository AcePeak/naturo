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
    _common._fail(json_output, "NOT_IMPLEMENTED", msg)
