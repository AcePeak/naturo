"""CLI commands for ``naturo browser`` subcommand.

Provides browser automation via Chrome DevTools Protocol (CDP).
The browser must be started with ``--remote-debugging-port=<port>``.
"""

from __future__ import annotations

import json as json_module
from typing import Optional

import click


@click.group()
@click.option("--port", type=int, default=9222, envvar="NATURO_CDP_PORT",
              help="Chrome DevTools Protocol port (default: 9222)")
@click.option("--host", default="localhost",
              help="Chrome DevTools host (default: localhost)")
@click.pass_context
def browser(ctx: click.Context, port: int, host: str) -> None:
    """Browser automation via Chrome DevTools Protocol.

    Requires Chrome/Chromium/Edge started with --remote-debugging-port.

    \b
    Examples:
        naturo browser navigate https://example.com
        naturo browser find "#search-input"
        naturo browser click "button.submit"
        naturo browser type "#search" "hello world"
        naturo browser screenshot --path page.png
    """
    ctx.ensure_object(dict)
    ctx.obj["cdp_port"] = port
    ctx.obj["cdp_host"] = host


def _get_page(ctx: click.Context):
    """Create a BrowserPage from context options.

    Returns:
        BrowserPage instance.

    Raises:
        SystemExit: If connection fails.
    """
    from naturo.browser import BrowserPage
    try:
        return BrowserPage(
            port=ctx.obj["cdp_port"],
            host=ctx.obj["cdp_host"],
        )
    except Exception as exc:
        click.echo(f"Error: Cannot connect to browser: {exc}", err=True)
        click.echo(
            "Make sure Chrome is running with "
            f"--remote-debugging-port={ctx.obj['cdp_port']}",
            err=True,
        )
        raise SystemExit(1)


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
    page = _get_page(ctx)
    try:
        page.navigate(url, wait_until=wait_until)
        if json_output:
            click.echo(json_module.dumps({
                "url": page.url,
                "title": page.title,
                "status": "ok",
            }))
        else:
            click.echo(f"Navigated to: {page.url}")
    finally:
        page.close()


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

    page = _get_page(ctx)
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
                click.echo(json_module.dumps({"elements": items, "count": len(items)}, indent=2))
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
                click.echo(json_module.dumps({
                    "ref": "e1",
                    "tag": el.tag_name,
                    "text": el.text[:200],
                    "value": el.value,
                }, indent=2))
            else:
                text = el.text[:80].replace("\n", "\\n")
                click.echo(f"  e1  [{el.tag_name}] {text}")
    except RuntimeError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
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

    page = _get_page(ctx)
    try:
        el = page.find(selector)
        el.click(offset_x=offset_x, offset_y=offset_y)
        if json_output:
            click.echo(json_module.dumps({"status": "ok", "selector": selector}))
        else:
            click.echo(f"Clicked: {selector}")
    except RuntimeError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
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

    page = _get_page(ctx)
    try:
        el = page.find(selector)
        el.type(text, clear_first=clear_first)
        if json_output:
            click.echo(json_module.dumps({"status": "ok", "selector": selector, "text": text}))
        else:
            click.echo(f"Typed into: {selector}")
    except RuntimeError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
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

    page = _get_page(ctx)
    try:
        el = page.find(selector)
        content = el.text
        if json_output:
            click.echo(json_module.dumps({"text": content, "selector": selector}))
        else:
            click.echo(content)
    except RuntimeError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
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

    page = _get_page(ctx)
    try:
        el = page.find(selector)
        value = el.attr(attribute)
        if json_output:
            click.echo(json_module.dumps({
                "attribute": attribute, "value": value, "selector": selector,
            }))
        else:
            click.echo(value if value is not None else "(null)")
    except RuntimeError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
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

    page = _get_page(ctx)
    try:
        el = page.find(selector)
        content = el.outer_html if outer else el.inner_html
        if json_output:
            click.echo(json_module.dumps({"html": content, "selector": selector}))
        else:
            click.echo(content)
    except RuntimeError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
    finally:
        page.close()


# ── Page operations ───────────────────────────────────────────────────────────


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
    page = _get_page(ctx)
    try:
        saved_path = page.screenshot(path, full_page=full_page)
        if json_output:
            click.echo(json_module.dumps({"path": saved_path, "status": "ok"}))
        else:
            click.echo(f"Screenshot saved: {saved_path}")
    finally:
        page.close()


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
    page = _get_page(ctx)
    try:
        result = page.evaluate(expression)
        if json_output:
            click.echo(json_module.dumps({"result": result}))
        else:
            click.echo(result)
    finally:
        page.close()


@browser.command("url")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def url_cmd(ctx: click.Context, json_output: bool) -> None:
    """Get the current page URL."""
    page = _get_page(ctx)
    try:
        current_url = page.url
        if json_output:
            click.echo(json_module.dumps({"url": current_url}))
        else:
            click.echo(current_url)
    finally:
        page.close()


@browser.command("title")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def title_cmd(ctx: click.Context, json_output: bool) -> None:
    """Get the current page title."""
    page = _get_page(ctx)
    try:
        current_title = page.title
        if json_output:
            click.echo(json_module.dumps({"title": current_title}))
        else:
            click.echo(current_title)
    finally:
        page.close()


# ── Wait ──────────────────────────────────────────────────────────────────────


@browser.command("wait")
@click.argument("selector")
@click.option("--by", type=click.Choice(["css", "xpath", "text"]),
              default=None, help="Force selector type")
@click.option("--timeout", type=float, default=30.0, help="Timeout in seconds (default: 30)")
@click.option("--state", type=click.Choice(["visible", "hidden", "attached", "detached"]),
              default="attached", help="Expected element state (default: attached)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def wait_cmd(ctx: click.Context, selector: str, by: Optional[str],
             timeout: float, state: str, json_output: bool) -> None:
    """Wait for an element to reach a specific state.

    \b
    Examples:
        naturo browser wait ".results-loaded" --timeout 10
        naturo browser wait "#spinner" --state hidden
    """
    if by:
        selector = f"{by}:{selector}"

    page = _get_page(ctx)
    try:
        page.wait_for(selector, timeout=timeout, state=state)
        if json_output:
            click.echo(json_module.dumps({"status": "ok", "selector": selector, "state": state}))
        else:
            click.echo(f"Element '{selector}' is {state}.")
    except TimeoutError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
    finally:
        page.close()


# ── Tab management ────────────────────────────────────────────────────────────


@browser.command("tabs")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def tabs_cmd(ctx: click.Context, json_output: bool) -> None:
    """List open browser tabs."""
    page = _get_page(ctx)
    try:
        tab_list = page.tabs()
        if json_output:
            click.echo(json_module.dumps(tab_list, indent=2))
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
    page = _get_page(ctx)
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
    page = _get_page(ctx)
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
            click.echo("Error: specify --to-bottom, --to-top, --to-element, or --by", err=True)
            raise SystemExit(1)

        if json_output:
            click.echo(json_module.dumps({"status": "ok", "action": msg}))
        else:
            click.echo(msg)
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

    page = _get_page(ctx)
    try:
        el = page.find(selector)
        el.hover()
        if json_output:
            click.echo(json_module.dumps({"status": "ok", "selector": selector}))
        else:
            click.echo(f"Hovered: {selector}")
    except RuntimeError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
    finally:
        page.close()


# ── Close ─────────────────────────────────────────────────────────────────────


@browser.command("close")
@click.pass_context
def close_cmd(ctx: click.Context) -> None:
    """Close the CDP connection."""
    page = _get_page(ctx)
    page.close()
    click.echo("Browser connection closed.")
