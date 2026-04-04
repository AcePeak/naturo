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


# ── Network (#765) ───────────────────────────────────────────────────────────


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
    page = _get_page(ctx)
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
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
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
    page = _get_page(ctx)
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


# ── Launch / Profiles (#758) ────────────────────────────────────────────────


@browser.command("launch")
@click.option("--profile", default=None,
              help="Chrome profile name or directory (e.g. 'Work', 'Profile 1')")
@click.option("--user-data-dir", default=None,
              help="Custom Chrome user data directory path")
@click.option("--headless", is_flag=True, help="Run in headless mode")
@click.option("--stealth", is_flag=True,
              help="Apply stealth flags to reduce bot fingerprinting")
@click.option("--url", default=None, help="Initial URL to open (default: about:blank)")
@click.option("--chrome-path", default=None,
              help="Explicit path to Chrome/Chromium/Edge binary")
@click.option("--timeout", type=float, default=15.0,
              help="Seconds to wait for CDP readiness (default: 15)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def launch_cmd(ctx: click.Context, profile: Optional[str],
               user_data_dir: Optional[str], headless: bool,
               stealth: bool, url: Optional[str],
               chrome_path: Optional[str], timeout: float,
               json_output: bool) -> None:
    """Launch Chrome with remote debugging enabled.

    Starts a new Chrome instance with --remote-debugging-port so naturo
    can connect to it. Optionally selects a Chrome profile.

    \b
    Examples:
        naturo browser launch
        naturo browser launch --profile Work
        naturo browser launch --profile "Profile 1" --headless
        naturo browser launch --user-data-dir /tmp/test-profile
        naturo browser launch --stealth --url https://example.com
    """
    from naturo.browser._launcher import launch_chrome as _launch_chrome
    from naturo.browser._stealth import STEALTH_FLAGS

    port = ctx.obj["cdp_port"]
    extra_args = list(STEALTH_FLAGS) if stealth else None

    try:
        proc = _launch_chrome(
            port=port,
            headless=headless,
            profile=profile,
            user_data_dir=user_data_dir,
            extra_args=extra_args,
            url=url,
            chrome_path=chrome_path,
            timeout=timeout,
        )
        if json_output:
            click.echo(json_module.dumps({
                "status": "ok",
                "pid": proc.pid,
                "port": proc.port,
                "profile": profile,
            }))
        else:
            click.echo(f"Chrome launched (pid={proc.pid}, port={proc.port})")
            if profile:
                click.echo(f"Profile: {profile}")
    except FileNotFoundError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
    except RuntimeError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)


@browser.command("profiles")
@click.option("--user-data-dir", default=None,
              help="Custom Chrome user data directory path")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def profiles_cmd(user_data_dir: Optional[str], json_output: bool) -> None:
    """List available Chrome profiles.

    Reads the Chrome 'Local State' file to discover profiles.
    No running browser required.

    \b
    Examples:
        naturo browser profiles
        naturo browser profiles --json
        naturo browser profiles --user-data-dir /custom/path
    """
    from naturo.browser._launcher import list_profiles as _list_profiles

    profiles = _list_profiles(user_data_dir=user_data_dir)

    if json_output:
        click.echo(json_module.dumps({"profiles": profiles, "count": len(profiles)}, indent=2))
    elif not profiles:
        click.echo("No Chrome profiles found.")
        click.echo("Hint: profiles are read from Chrome's 'Local State' file.")
    else:
        click.echo(f"Found {len(profiles)} profile(s):")
        for p in profiles:
            click.echo(f"  {p['name']:<20} [{p['directory']}]  {p['path']}")


# ── Stealth / anti-detection (#760) ──────────────────────────────────────────


@browser.command("stealth")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def stealth_cmd(ctx: click.Context, json_output: bool) -> None:
    """Apply anti-detection patches to the running browser.

    Injects JavaScript patches that mask common bot fingerprints
    (navigator.webdriver, plugins, languages, WebGL vendor, etc.).
    Patches persist across page navigations.

    \\b
    Examples:
        naturo browser stealth
        naturo browser stealth --json
    """
    from naturo.browser._stealth import apply_stealth_patches

    page = _get_page(ctx)
    try:
        count = apply_stealth_patches(page)
        if json_output:
            click.echo(json_module.dumps({
                "success": True,
                "patches_applied": count,
            }))
        else:
            click.echo(f"Applied {count} stealth patches.")
    except Exception as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
    finally:
        page.close()


@browser.command("stealth-flags")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def stealth_flags_cmd(json_output: bool) -> None:
    """Print Chrome flags for anti-detection.

    These flags should be passed when launching Chrome to reduce
    automation fingerprinting. No running browser required.

    \\b
    Examples:
        naturo browser stealth-flags
        chrome $(naturo browser stealth-flags)
    """
    from naturo.browser._stealth import STEALTH_FLAGS

    if json_output:
        click.echo(json_module.dumps({"flags": STEALTH_FLAGS}))
    else:
        click.echo(" ".join(STEALTH_FLAGS))


# ── Captcha ───────────────────────────────────────────────────────────────────


@browser.command("captcha-detect")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def captcha_detect(ctx: click.Context, json_output: bool) -> None:
    """Detect captchas on the current page.

    Scans for reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile,
    and generic captcha iframes.

    \b
    Examples:
        naturo browser captcha-detect
        naturo browser captcha-detect --json
    """
    page = _get_page(ctx)
    from naturo.browser._captcha import CaptchaManager

    manager = CaptchaManager(page)
    captchas = manager.detect()

    if json_output:
        click.echo(json_module.dumps({"captchas": captchas, "count": len(captchas)}))
    elif not captchas:
        click.echo("No captchas detected on this page.")
    else:
        click.echo(f"Detected {len(captchas)} captcha(s):")
        for i, c in enumerate(captchas, 1):
            visible = "visible" if c.get("visible") else "hidden"
            sitekey = c.get("sitekey", "")
            key_display = f" (sitekey: {sitekey[:20]}...)" if sitekey else ""
            click.echo(f"  {i}. {c['type']} [{visible}]{key_display}")


@browser.command("captcha-solve")
@click.option("--solver", type=click.Choice(["manual", "token"]), default="manual",
              help="Solver strategy (default: manual)")
@click.option("--token", default=None,
              help="Pre-obtained captcha token (required for 'token' solver)")
@click.option("--timeout", type=float, default=120.0,
              help="Timeout for manual solving (default: 120s)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def captcha_solve(ctx: click.Context, solver: str, token: Optional[str],
                  timeout: float, json_output: bool) -> None:
    """Solve a captcha on the current page.

    \b
    Solver strategies:
      manual   — Wait for user to solve captcha in browser (default)
      token    — Inject a pre-obtained token (e.g. from 2Captcha)

    \b
    Examples:
        naturo browser captcha-solve --solver manual --timeout 60
        naturo browser captcha-solve --solver token --token "03AGdBq24..."
    """
    page = _get_page(ctx)
    from naturo.browser._captcha import (
        CaptchaManager,
        CaptchaError,
        CaptchaSolver,
        ManualSolver,
        TokenInjectionSolver,
    )

    manager = CaptchaManager(page)

    solver_instance: CaptchaSolver
    if solver == "token":
        if not token:
            click.echo("Error: --token is required when using 'token' solver", err=True)
            raise SystemExit(1)
        solver_instance = TokenInjectionSolver(token=token)
    else:
        solver_instance = ManualSolver(timeout=timeout)

    try:
        result_token = manager.solve(solver=solver_instance)
        if json_output:
            click.echo(json_module.dumps({
                "success": True,
                "solver": solver,
                "token_length": len(result_token),
            }))
        else:
            click.echo(f"Captcha solved ({len(result_token)} chars)")
    except CaptchaError as exc:
        if json_output:
            click.echo(json_module.dumps({
                "success": False,
                "error": str(exc),
            }))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)


# ── Wait mechanisms (#762) ───────────────────────────────────────────────────


@browser.command("wait-navigation")
@click.option("--timeout", type=float, default=30.0,
              help="Timeout in seconds (default: 30)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def wait_navigation_cmd(ctx: click.Context, timeout: float,
                        json_output: bool) -> None:
    """Wait for a navigation to complete (URL change + page load).

    \b
    Examples:
        naturo browser wait-navigation
        naturo browser wait-navigation --timeout 10
    """
    page = _get_page(ctx)
    try:
        new_url = page.wait_for_navigation(timeout=timeout)
        if json_output:
            click.echo(json_module.dumps({"status": "ok", "url": new_url}))
        else:
            click.echo(f"Navigation complete: {new_url}")
    except TimeoutError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
    finally:
        page.close()


@browser.command("wait-url")
@click.argument("pattern")
@click.option("--regex", is_flag=True, help="Treat pattern as a regular expression")
@click.option("--timeout", type=float, default=30.0,
              help="Timeout in seconds (default: 30)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def wait_url_cmd(ctx: click.Context, pattern: str, regex: bool,
                 timeout: float, json_output: bool) -> None:
    """Wait until the page URL matches a pattern.

    PATTERN is a substring to match (or regex with --regex).

    \b
    Examples:
        naturo browser wait-url "/dashboard"
        naturo browser wait-url "order_id=\\d+" --regex
    """
    page = _get_page(ctx)
    try:
        matched_url = page.wait_for_url(pattern, regex=regex, timeout=timeout)
        if json_output:
            click.echo(json_module.dumps({"status": "ok", "url": matched_url}))
        else:
            click.echo(f"URL matched: {matched_url}")
    except TimeoutError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
    finally:
        page.close()


@browser.command("wait-function")
@click.argument("expression")
@click.option("--timeout", type=float, default=30.0,
              help="Timeout in seconds (default: 30)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def wait_function_cmd(ctx: click.Context, expression: str,
                      timeout: float, json_output: bool) -> None:
    """Wait until a JavaScript expression returns a truthy value.

    EXPRESSION is evaluated repeatedly until truthy or timeout.

    \b
    Examples:
        naturo browser wait-function "document.querySelector('.loaded')"
        naturo browser wait-function "window.appReady === true" --timeout 15
    """
    page = _get_page(ctx)
    try:
        result = page.wait_for_function(expression, timeout=timeout)
        if json_output:
            click.echo(json_module.dumps({"status": "ok", "result": str(result)}))
        else:
            click.echo(f"Expression truthy: {result}")
    except TimeoutError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
    finally:
        page.close()


@browser.command("wait-network-idle")
@click.option("--idle-time", type=float, default=0.5,
              help="Seconds of silence to consider idle (default: 0.5)")
@click.option("--timeout", type=float, default=30.0,
              help="Timeout in seconds (default: 30)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def wait_network_idle_cmd(ctx: click.Context, idle_time: float,
                          timeout: float, json_output: bool) -> None:
    """Wait until no new network requests are being made.

    \b
    Examples:
        naturo browser wait-network-idle
        naturo browser wait-network-idle --idle-time 1.0 --timeout 60
    """
    page = _get_page(ctx)
    try:
        page.wait_for_network_idle(idle_time=idle_time, timeout=timeout)
        if json_output:
            click.echo(json_module.dumps({"status": "ok"}))
        else:
            click.echo("Network is idle.")
    except TimeoutError as exc:
        if json_output:
            click.echo(json_module.dumps({"error": str(exc)}))
        else:
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)
    finally:
        page.close()
