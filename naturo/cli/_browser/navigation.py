"""Browser navigation and page-level commands: navigate, url, title, scroll, eval, close, tabs, tab."""

from __future__ import annotations

from naturo.cli._jsonio import json_dumps
from typing import Optional

import click

from naturo.cli import browser_cmd
from naturo.cli._browser._group import browser
from naturo.cli.error_helpers import emit_error


# ── Navigate ──────────────────────────────────────────────────────────────────


@browser.command()
@click.argument("url")
@click.option("--wait-until", type=click.Choice(["load", "domcontentloaded", "networkidle"]),
              default="load", help="Wait strategy (default: load)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def navigate(ctx: click.Context, url: str, wait_until: str, json_output: bool) -> None:
    """Navigate to a URL.

    \b
    Examples:
        naturo browser navigate https://example.com
        naturo browser navigate https://example.com --wait-until networkidle
    """
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        page.navigate(url, wait_until=wait_until)
        if json_output:
            click.echo(json_dumps({
                "url": page.url,
                "title": page.title,
                "status": "ok",
            }))
        else:
            click.echo(f"Navigated to: {page.url}")
    finally:
        page.close()


# ── Page operations (eval / url / title) ──────────────────────────────────────


@browser.command("eval")
@click.argument("expression")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def eval_cmd(ctx: click.Context, expression: str, json_output: bool) -> None:
    """Evaluate a JavaScript expression.

    \b
    Examples:
        naturo browser eval "document.title"
        naturo browser eval "1 + 1" --json
    """
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        result = page.evaluate(expression)
        if json_output:
            click.echo(json_dumps({"result": result}))
        else:
            click.echo(result)
    finally:
        page.close()


@browser.command("url")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def url_cmd(ctx: click.Context, json_output: bool) -> None:
    """Get the current page URL."""
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        current_url = page.url
        if json_output:
            click.echo(json_dumps({"url": current_url}))
        else:
            click.echo(current_url)
    finally:
        page.close()


@browser.command("title")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def title_cmd(ctx: click.Context, json_output: bool) -> None:
    """Get the current page title."""
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        current_title = page.title
        if json_output:
            click.echo(json_dumps({"title": current_title}))
        else:
            click.echo(current_title)
    finally:
        page.close()


# ── Tab management ────────────────────────────────────────────────────────────


@browser.command("tabs")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def tabs_cmd(ctx: click.Context, json_output: bool) -> None:
    """List open browser tabs."""
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        tab_list = page.tabs()
        if json_output:
            click.echo(json_dumps(tab_list, indent=2))
        else:
            for i, tab in enumerate(tab_list):
                click.echo(f"  {i + 1}. [{tab.get('id', '')[:8]}] {tab.get('title', '')} — {tab.get('url', '')}")
    finally:
        page.close()


@browser.command("tab")
@click.argument("tab_id")
@click.pass_context
def tab_cmd(ctx: click.Context, tab_id: str) -> None:
    """Switch to a specific tab by ID."""
    page = browser_cmd._get_page(ctx)
    try:
        page.switch_tab(tab_id)
        click.echo(f"Switched to tab: {tab_id}")
    finally:
        page.close()


# ── Scroll ────────────────────────────────────────────────────────────────────


@browser.command("scroll")
@click.option("--to-bottom", is_flag=True, help="Scroll to page bottom")
@click.option("--to-top", is_flag=True, help="Scroll to page top")
@click.option("--to-element", default=None, help="Scroll element into view (CSS selector)")
@click.option("--by", "by_pixels", type=int, default=None,
              help="Scroll by N pixels (positive=down, negative=up)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def scroll_cmd(ctx: click.Context, to_bottom: bool, to_top: bool,
               to_element: Optional[str], by_pixels: Optional[int],
               json_output: bool) -> None:
    """Scroll the page.

    \b
    Examples:
        naturo browser scroll --to-bottom
        naturo browser scroll --to-top
        naturo browser scroll --to-element "#footer"
        naturo browser scroll --by 500
    """
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        if to_bottom:
            page.scroll_to_bottom()
            msg = "Scrolled to bottom"
        elif to_top:
            page.scroll_to_top()
            msg = "Scrolled to top"
        elif to_element:
            page.scroll_to_element(to_element)
            msg = f"Scrolled to element: {to_element}"
        elif by_pixels is not None:
            page.scroll_by(by_pixels)
            msg = f"Scrolled by {by_pixels}px"
        else:
            emit_error(
                "INVALID_INPUT",
                "specify --to-bottom, --to-top, --to-element, or --by",
                json_output,
            )

        if json_output:
            click.echo(json_dumps({"status": "ok", "action": msg}))
        else:
            click.echo(msg)
    finally:
        page.close()


# ── Close ─────────────────────────────────────────────────────────────────────


@browser.command("close")
@click.pass_context
def close_cmd(ctx: click.Context) -> None:
    """Close the CDP connection."""
    page = browser_cmd._get_page(ctx)
    page.close()
    click.echo("Browser connection closed.")
