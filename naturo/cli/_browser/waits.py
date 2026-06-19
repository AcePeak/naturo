"""Browser wait commands (#762): wait, wait-navigation, wait-url, wait-function, wait-network-idle."""

from __future__ import annotations

from naturo.cli._jsonio import json_dumps
from typing import Optional

import click

from naturo.cli import browser_cmd
from naturo.cli._browser._group import browser
from naturo.cli.error_helpers import emit_exception_error


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

    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        page.wait_for(selector, timeout=timeout, state=state)
        if json_output:
            click.echo(json_dumps({"status": "ok", "selector": selector, "state": state}))
        else:
            click.echo(f"Element '{selector}' is {state}.")
    except TimeoutError as exc:
        emit_exception_error(exc, json_output, fallback_code="TIMEOUT")
    finally:
        page.close()


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
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        new_url = page.wait_for_navigation(timeout=timeout)
        if json_output:
            click.echo(json_dumps({"status": "ok", "url": new_url}))
        else:
            click.echo(f"Navigation complete: {new_url}")
    except TimeoutError as exc:
        emit_exception_error(exc, json_output, fallback_code="TIMEOUT")
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
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        matched_url = page.wait_for_url(pattern, regex=regex, timeout=timeout)
        if json_output:
            click.echo(json_dumps({"status": "ok", "url": matched_url}))
        else:
            click.echo(f"URL matched: {matched_url}")
    except TimeoutError as exc:
        emit_exception_error(exc, json_output, fallback_code="TIMEOUT")
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
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        result = page.wait_for_function(expression, timeout=timeout)
        if json_output:
            click.echo(json_dumps({"status": "ok", "result": str(result)}))
        else:
            click.echo(f"Expression truthy: {result}")
    except TimeoutError as exc:
        emit_exception_error(exc, json_output, fallback_code="TIMEOUT")
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
    page = browser_cmd._get_page(ctx, json_output=json_output)
    try:
        page.wait_for_network_idle(idle_time=idle_time, timeout=timeout)
        if json_output:
            click.echo(json_dumps({"status": "ok"}))
        else:
            click.echo("Network is idle.")
    except TimeoutError as exc:
        emit_exception_error(exc, json_output, fallback_code="TIMEOUT")
    finally:
        page.close()
