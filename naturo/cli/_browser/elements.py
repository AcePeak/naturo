"""Browser element commands: find, click, type, select, text, attr, html, hover."""

from __future__ import annotations

from naturo.cli._jsonio import json_dumps
from typing import Optional

import click

from naturo.cli import browser_cmd
from naturo.cli._browser._group import browser
from naturo.cli.error_helpers import emit_exception_error


# ── Find ──────────────────────────────────────────────────────────────────────


@browser.command("find")
@click.argument("selector")
@click.option("--by", type=click.Choice(["css", "xpath", "text"]),
              default=None, help="Force selector type (default: auto-detect)")
@click.option("--all", "find_all", is_flag=True, help="Find all matching elements")
@click.option("--timeout", type=float, default=None, help="Wait timeout in seconds")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def find_cmd(ctx: click.Context, selector: str, by: Optional[str],
             find_all: bool, timeout: Optional[float], json_output: bool) -> None:
    """Find elements on the page.

    \b
    Selector auto-detection:
        #foo, .bar      → CSS
        //div, /html    → XPath
        "Login"         → text search

    Use --by to override auto-detection.

    \b
    Examples:
        naturo browser find "#search-input"
        naturo browser find "//div[@class='item']" --all
        naturo browser find "text:Login" --timeout 5
    """
    if by:
        selector = f"{by}:{selector}"

    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        if timeout is not None:
            page.wait_for(selector, timeout=timeout)

        if find_all:
            elements = page.find_all(selector)
            if json_output:
                items = []
                for i, el in enumerate(elements):
                    items.append({
                        "ref": f"e{i + 1}",
                        "tag": el.tag_name,
                        "text": el.text[:200],
                    })
                click.echo(json_dumps({"elements": items, "count": len(items)}, indent=2))
            else:
                if not elements:
                    click.echo("No elements found.")
                else:
                    for i, el in enumerate(elements):
                        text = el.text[:80].replace("\n", "\\n")
                        click.echo(f"  e{i + 1}  [{el.tag_name}] {text}")
                    click.echo(f"\n{len(elements)} element(s) found.")
        else:
            el = page.find(selector)
            if json_output:
                click.echo(json_dumps({
                    "ref": "e1",
                    "tag": el.tag_name,
                    "text": el.text[:200],
                    "value": el.value,
                }, indent=2))
            else:
                text = el.text[:80].replace("\n", "\\n")
                click.echo(f"  e1  [{el.tag_name}] {text}")
    except RuntimeError as exc:
        emit_exception_error(exc, json_output, fallback_code="ELEMENT_NOT_FOUND")
    finally:
        page.close()


# ── Click ─────────────────────────────────────────────────────────────────────


@browser.command("click")
@click.argument("selector")
@click.option("--by", type=click.Choice(["css", "xpath", "text"]),
              default=None, help="Force selector type")
@click.option("--offset-x", type=int, default=0,
              help="X offset from element top-left (0 = center)")
@click.option("--offset-y", type=int, default=0,
              help="Y offset from element top-left (0 = center)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def click_cmd(ctx: click.Context, selector: str, by: Optional[str],
              offset_x: int, offset_y: int, json_output: bool) -> None:
    """Click an element on the page.

    \b
    Examples:
        naturo browser click "button.submit"
        naturo browser click "#captcha-image" --offset-x 123 --offset-y 45
        naturo browser click "text:Login"
    """
    if by:
        selector = f"{by}:{selector}"

    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        el = page.find(selector)
        el.click(offset_x=offset_x, offset_y=offset_y)
        if json_output:
            click.echo(json_dumps({"status": "ok", "selector": selector}))
        else:
            click.echo(f"Clicked: {selector}")
    except RuntimeError as exc:
        emit_exception_error(exc, json_output, fallback_code="ELEMENT_NOT_FOUND")
    finally:
        page.close()


# ── Type ──────────────────────────────────────────────────────────────────────


@browser.command("type")
@click.argument("selector")
@click.argument("text")
@click.option("--by", type=click.Choice(["css", "xpath", "text"]),
              default=None, help="Force selector type")
@click.option("--clear-first", is_flag=True, help="Clear element value before typing")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def type_cmd(ctx: click.Context, selector: str, text: str, by: Optional[str],
             clear_first: bool, json_output: bool) -> None:
    """Type text into an element.

    \b
    Examples:
        naturo browser type "#search" "hello world"
        naturo browser type "input[name=email]" "user@example.com" --clear-first
    """
    if by:
        selector = f"{by}:{selector}"

    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        el = page.find(selector)
        el.type(text, clear_first=clear_first)
        if json_output:
            click.echo(json_dumps({"status": "ok", "selector": selector, "text": text}))
        else:
            click.echo(f"Typed into: {selector}")
    except RuntimeError as exc:
        emit_exception_error(exc, json_output, fallback_code="ELEMENT_NOT_FOUND")
    finally:
        page.close()


# ── Select ───────────────────────────────────────────────────────────────────


@browser.command("select")
@click.argument("selector")
@click.argument("value")
@click.option("--by", type=click.Choice(["css", "xpath", "text"]),
              default=None, help="Force selector type")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def select_cmd(ctx: click.Context, selector: str, value: str,
               by: Optional[str], json_output: bool) -> None:
    """Select an option from a <select> dropdown.

    VALUE matches against option value attributes first, then text content.

    \b
    Examples:
        naturo browser select "#country" "US"
        naturo browser select "select[name=lang]" "English"
    """
    if by:
        selector = f"{by}:{selector}"

    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        el = page.find(selector)
        el.select(value)
        if json_output:
            click.echo(json_dumps({
                "status": "ok", "selector": selector, "value": value,
            }))
        else:
            click.echo(f"Selected '{value}' in: {selector}")
    except RuntimeError as exc:
        emit_exception_error(exc, json_output, fallback_code="ELEMENT_NOT_FOUND")
    finally:
        page.close()


# ── Text / Attr / HTML ────────────────────────────────────────────────────────


@browser.command("text")
@click.argument("selector")
@click.option("--by", type=click.Choice(["css", "xpath", "text"]),
              default=None, help="Force selector type")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def text_cmd(ctx: click.Context, selector: str, by: Optional[str], json_output: bool) -> None:
    """Get the text content of an element.

    \b
    Examples:
        naturo browser text "h1"
        naturo browser text ".price" --json
    """
    if by:
        selector = f"{by}:{selector}"

    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        el = page.find(selector)
        content = el.text
        if json_output:
            click.echo(json_dumps({"text": content, "selector": selector}))
        else:
            click.echo(content)
    except RuntimeError as exc:
        emit_exception_error(exc, json_output, fallback_code="ELEMENT_NOT_FOUND")
    finally:
        page.close()


@browser.command("attr")
@click.argument("selector")
@click.argument("attribute")
@click.option("--by", type=click.Choice(["css", "xpath", "text"]),
              default=None, help="Force selector type")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def attr_cmd(ctx: click.Context, selector: str, attribute: str,
             by: Optional[str], json_output: bool) -> None:
    """Get an attribute value from an element.

    \b
    Examples:
        naturo browser attr "a.link" href
        naturo browser attr "img" src --json
    """
    if by:
        selector = f"{by}:{selector}"

    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        el = page.find(selector)
        value = el.attr(attribute)
        if json_output:
            click.echo(json_dumps({
                "attribute": attribute, "value": value, "selector": selector,
            }))
        else:
            click.echo(value if value is not None else "(null)")
    except RuntimeError as exc:
        emit_exception_error(exc, json_output, fallback_code="ELEMENT_NOT_FOUND")
    finally:
        page.close()


@browser.command("html")
@click.argument("selector")
@click.option("--by", type=click.Choice(["css", "xpath", "text"]),
              default=None, help="Force selector type")
@click.option("--outer", is_flag=True, help="Get outerHTML instead of innerHTML")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def html_cmd(ctx: click.Context, selector: str, by: Optional[str],
             outer: bool, json_output: bool) -> None:
    """Get the HTML content of an element.

    \b
    Examples:
        naturo browser html "#content"
        naturo browser html "div.card" --outer
    """
    if by:
        selector = f"{by}:{selector}"

    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        el = page.find(selector)
        content = el.outer_html if outer else el.inner_html
        if json_output:
            click.echo(json_dumps({"html": content, "selector": selector}))
        else:
            click.echo(content)
    except RuntimeError as exc:
        emit_exception_error(exc, json_output, fallback_code="ELEMENT_NOT_FOUND")
    finally:
        page.close()


# ── Hover ─────────────────────────────────────────────────────────────────────


@browser.command("hover")
@click.argument("selector")
@click.option("--by", type=click.Choice(["css", "xpath", "text"]),
              default=None, help="Force selector type")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def hover_cmd(ctx: click.Context, selector: str, by: Optional[str],
              json_output: bool) -> None:
    """Hover over an element.

    \b
    Examples:
        naturo browser hover ".dropdown-trigger"
        naturo browser hover "text:Menu"
    """
    if by:
        selector = f"{by}:{selector}"

    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        el = page.find(selector)
        el.hover()
        if json_output:
            click.echo(json_dumps({"status": "ok", "selector": selector}))
        else:
            click.echo(f"Hovered: {selector}")
    except RuntimeError as exc:
        emit_exception_error(exc, json_output, fallback_code="ELEMENT_NOT_FOUND")
    finally:
        page.close()
