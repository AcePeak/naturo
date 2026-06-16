"""The ``naturo browser`` Click group.

Defined in its own module (with no dependency on the command submodules or on
``browser_cmd``) so the focused command modules can attach to it without forming
an import cycle. ``naturo.cli.browser_cmd`` re-exports ``browser`` from here.
"""

from __future__ import annotations

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
