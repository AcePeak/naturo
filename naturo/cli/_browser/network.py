"""Browser network commands (#765): requests, intercept."""

from __future__ import annotations

import json as json_module
from typing import Optional

import click

from naturo.cli import browser_cmd
from naturo.cli._browser._group import browser
from naturo.cli.error_helpers import emit_exception_error


@browser.command("requests")
@click.option("--pattern", default=None, help="URL glob filter (e.g. '*/api/*')")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def requests_cmd(ctx: click.Context, pattern: Optional[str], json_output: bool) -> None:
    """List recent network requests captured by the page.

    \\b
    Examples:
        naturo browser requests
        naturo browser requests --pattern '*/api/*'
        naturo browser requests --json
    """
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        snapshot = page.network.capture_snapshot()
        if pattern:
            snapshot = page.network.find_requests(pattern, snapshot=snapshot)

        if json_output:
            click.echo(json_module.dumps({
                "success": True,
                "requests": snapshot,
                "count": len(snapshot),
            }, indent=2))
        else:
            if not snapshot:
                click.echo("No requests captured.")
            else:
                for r in snapshot:
                    size_kb = r.get("size", 0) / 1024
                    click.echo(f"  {r.get('type', '?'):<10} {size_kb:>8.1f} KB  {r.get('name', '')[:80]}")
                click.echo(f"\n{len(snapshot)} request(s)")
    except Exception as exc:
        emit_exception_error(exc, json_output)
    finally:
        page.close()


@browser.command("intercept")
@click.argument("pattern")
@click.option("--action", type=click.Choice(["abort", "fulfill"]), default="abort",
              help="Action: abort (block) or fulfill (mock response)")
@click.option("--body", default=None, help="Response body (for fulfill)")
@click.option("--status", type=int, default=200, help="HTTP status code (for fulfill)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def intercept_cmd(ctx: click.Context, pattern: str, action: str,
                  body: Optional[str], status: int, json_output: bool) -> None:
    """Add a request interception rule.

    \\b
    Examples:
        naturo browser intercept '*/tracking/*' --action abort
        naturo browser intercept '*/config.json' --action fulfill --body '{"debug":true}'
    """
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        if action == "abort":
            page.network.abort_pattern(pattern)
        elif action == "fulfill":
            page.network.mock_response(
                pattern, body=body or "", status_code=status,
            )

        if json_output:
            click.echo(json_module.dumps({
                "success": True,
                "pattern": pattern,
                "action": action,
            }))
        else:
            click.echo(f"Interception rule added: {action} {pattern}")
    except Exception as exc:
        emit_exception_error(exc, json_output)
    finally:
        page.close()
