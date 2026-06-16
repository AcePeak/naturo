"""Browser visual commands: screenshot."""

from __future__ import annotations

import json as json_module
from typing import Optional

import click

from naturo.cli import browser_cmd
from naturo.cli._browser._group import browser
from naturo.cli.error_helpers import emit_exception_error


@browser.command("screenshot")
@click.option("--path", default="screenshot.png", help="Output file path")
@click.option("--selector", default=None, help="Capture only this element (CSS selector)")
@click.option("--full-page", is_flag=True, help="Capture full scrollable page")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def screenshot_cmd(ctx: click.Context, path: str, selector: Optional[str],
                   full_page: bool, json_output: bool) -> None:
    """Take a screenshot of the page.

    \b
    Examples:
        naturo browser screenshot --path page.png
        naturo browser screenshot --full-page --path full.png
    """
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        saved_path = page.screenshot(path, full_page=full_page)
        if json_output:
            click.echo(json_module.dumps({"path": saved_path, "status": "ok"}))
        else:
            click.echo(f"Screenshot saved: {saved_path}")
    except RuntimeError as exc:
        emit_exception_error(exc, json_output, fallback_code="SCREENSHOT_FAILED")
    finally:
        page.close()
