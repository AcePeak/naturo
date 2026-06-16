"""CLI commands for ``naturo browser`` subcommand.

Provides browser automation via Chrome DevTools Protocol (CDP).
The browser must be started with ``--remote-debugging-port=<port>``.

The top-level ``browser`` Click group lives in ``naturo.cli._browser._group``
(re-exported here); the shared ``_get_page`` helper is defined here so existing
``@patch("naturo.cli.browser_cmd._get_page")`` test targets keep working. The
individual subcommands live in focused modules under ``naturo/cli/_browser/`` and
are imported at the bottom of this file, which both registers them on the
``browser`` group and re-exports the command callables so that
``from naturo.cli.browser_cmd import <command>`` keeps working.
"""

from __future__ import annotations

import click

from naturo.cli._browser._group import browser  # noqa: F401  (re-export)
from naturo.cli.error_helpers import emit_error


def _get_page(ctx: click.Context, *, json_output: bool = False):
    """Create a BrowserPage from context options.

    Args:
        ctx: Click context with cdp_port and cdp_host.
        json_output: When True, emit structured JSON error on failure.

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
        port = ctx.obj['cdp_port']
        msg = (
            f"Cannot connect to browser: {exc}. "
            f"Make sure Chrome is running with "
            f"--remote-debugging-port={port}"
        )
        emit_error(
            "BROWSER_CONNECTION_ERROR", msg, json_output,
            suggested_action=(
                "Launch Chrome with --remote-debugging-port: "
                "'naturo browser launch' or "
                f"'chrome --remote-debugging-port={port}'"
            ),
            recoverable=True,
        )


# Subcommand implementations live in focused modules under ``naturo/cli/_browser/``.
# Importing them registers each command on the ``browser`` group defined above and
# re-exports the command callables for backward compatibility.
from naturo.cli._browser.navigation import (  # noqa: E402,F401
    close_cmd,
    eval_cmd,
    navigate,
    scroll_cmd,
    tab_cmd,
    tabs_cmd,
    title_cmd,
    url_cmd,
)
from naturo.cli._browser.elements import (  # noqa: E402,F401
    attr_cmd,
    click_cmd,
    find_cmd,
    hover_cmd,
    html_cmd,
    select_cmd,
    text_cmd,
    type_cmd,
)
from naturo.cli._browser.frames import (  # noqa: E402,F401
    frame_eval_cmd,
    frame_find_cmd,
    frames_cmd,
)
from naturo.cli._browser.waits import (  # noqa: E402,F401
    wait_cmd,
    wait_function_cmd,
    wait_navigation_cmd,
    wait_network_idle_cmd,
    wait_url_cmd,
)
from naturo.cli._browser.network import (  # noqa: E402,F401
    intercept_cmd,
    requests_cmd,
)
from naturo.cli._browser.visual import screenshot_cmd  # noqa: E402,F401
from naturo.cli._browser.stealth import (  # noqa: E402,F401
    stealth_check_cmd,
    stealth_cmd,
    stealth_flags_cmd,
)
from naturo.cli._browser.lifecycle import (  # noqa: E402,F401
    download_cmd,
    launch_cmd,
    profiles_cmd,
)
from naturo.cli._browser.captcha import (  # noqa: E402,F401
    captcha_detect,
    captcha_solve,
)
