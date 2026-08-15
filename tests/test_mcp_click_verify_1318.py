"""MCP click hit-window verification parity with the CLI (#1318).

Split from #1207, which gave the *CLI* ``naturo click`` a landing-window honesty
check: after the click it reports the top-level window actually under the point,
fails loudly with ``CLICK_WRONG_WINDOW`` when a known target belongs to a
different process (occluded / never foregrounded), and discloses ``hit_window``
for bare coordinates. #1318 brings the *MCP* ``click`` tool to the same bar,
reusing the shared ``naturo.hit_verify`` implementation so both surfaces return
an identical verdict.

Every test patches the window-hit-test helpers (``_window_root_at_point`` /
``_window_pid``), so they are desktop-independent and send no real input.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

from click.testing import CliRunner

mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:  # pragma: no cover - mcp optional
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


# ── MCP invocation harness ────────────────────────────────────────────────


def _call_mcp_click(arguments, *, hit, target_pid):
    """Call the MCP ``click`` tool with the hit-test helpers patched.

    Args:
        arguments: kwargs passed to the click tool.
        hit: tuple returned by _window_root_at_point, or None.
        target_pid: value returned by _window_pid for the target hwnd.

    Returns:
        (payload_dict, backend_mock)
    """
    backend = MagicMock()
    with patch("naturo.mcp_server.get_backend", return_value=backend), \
         patch("naturo.cli.interaction._check_desktop_session"), \
         patch("naturo.mcp._input._window_root_at_point", return_value=hit), \
         patch("naturo.mcp._input._window_pid", return_value=target_pid):
        server = create_server()

        async def _run():
            return await server.call_tool("click", arguments)

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(_run())
        finally:
            loop.close()
    content = result[0] if isinstance(result, tuple) else result
    return json.loads(content[0].text), backend


# ── MCP behaviour ─────────────────────────────────────────────────────────


def test_mcp_targeted_click_on_other_process_fails_loudly():
    """A known hwnd target occluded by another process → CLICK_WRONG_WINDOW."""
    payload, backend = _call_mcp_click(
        {"x": 500, "y": 300, "hwnd": 349525},
        hit=(777, "WindowsTerminal", 999),  # different pid under the point
        target_pid=111,
    )
    assert payload["success"] is False
    assert payload["error"]["code"] == "CLICK_WRONG_WINDOW"
    # The click was attempted (parity with the CLI, which also injects then
    # checks) but the tool refuses to claim a success that did not happen.
    backend.click.assert_called_once()


def test_mcp_bare_coords_discloses_hit_window():
    """Bare coords (no known target) cannot fail, but discloses the hit window."""
    payload, backend = _call_mcp_click(
        {"x": 500, "y": 300},
        hit=(777, "WindowsTerminal", 999),
        target_pid=None,
    )
    assert payload["success"] is True
    assert payload["hit_window"] == {"hwnd": 777, "title": "WindowsTerminal", "pid": 999}
    # No known intent for bare coordinates → cannot positively verify.
    assert payload["verified"] is None


def test_mcp_targeted_click_same_process_succeeds_and_verifies():
    """A click landing on the target's own process is a verified success."""
    payload, backend = _call_mcp_click(
        {"x": 500, "y": 300, "hwnd": 349525},
        hit=(349525, "Target App", 111),  # same pid as the target
        target_pid=111,
    )
    assert payload["success"] is True
    assert payload["verified"] is True
    assert payload["hit_window"]["pid"] == 111
    backend.click.assert_called_once()
    backend.focus_window.assert_called_once()  # target was brought forward first


def test_mcp_no_hit_info_omits_hit_window():
    """When the hit window is undeterminable, the payload omits hit_window."""
    payload, backend = _call_mcp_click(
        {"x": 500, "y": 300},
        hit=None,
        target_pid=None,
    )
    assert payload["success"] is True
    assert "hit_window" not in payload
    assert payload["verified"] is None
    backend.click.assert_called_once()


# ── CLI ↔ MCP contract: identical verdict for the same scenario ───────────


def _invoke_cli_click(args, *, hit, target_pid):
    """Invoke the CLI click_cmd with the window hit-test helpers patched."""
    from naturo.cli.interaction import click_cmd

    backend = MagicMock()
    backend._resolve_hwnd.return_value = 349525
    backend._is_afh_window.return_value = False
    backend._is_winui_window.return_value = False
    with patch("naturo.cli.interaction._common._get_backend", return_value=backend), \
         patch("naturo.cli.interaction._common._auto_route", return_value={}), \
         patch("naturo.cli.interaction._click._window_root_at_point", return_value=hit), \
         patch("naturo.cli.interaction._click._window_pid", return_value=target_pid):
        runner = CliRunner()
        return runner.invoke(click_cmd, args + ["--no-verify", "-j"])


def _cli_verdict(cli_result):
    """Reduce a CLI click result to a comparable (ok, code) verdict."""
    data = json.loads(cli_result.output)
    if cli_result.exit_code == 0 and data.get("success", True):
        return (True, None)
    code = (data.get("error") or {}).get("code") or data.get("code")
    return (False, code)


def _mcp_verdict(payload):
    """Reduce an MCP click payload to a comparable (ok, code) verdict."""
    if payload.get("success"):
        return (True, None)
    return (False, payload.get("error", {}).get("code"))


def test_cli_and_mcp_agree_on_wrong_window_verdict():
    """Contract (#1318 acceptance): same occluded-target scenario, same verdict.

    A coordinate click on a known target (hwnd) that lands on a *different
    process'* window must fail loudly with CLICK_WRONG_WINDOW on BOTH surfaces.
    """
    hit = (777, "WindowsTerminal", 999)
    target_pid = 111

    cli_result = _invoke_cli_click(
        ["--coords", "500", "300", "--hwnd", "349525"],
        hit=hit, target_pid=target_pid,
    )
    mcp_payload, _ = _call_mcp_click(
        {"x": 500, "y": 300, "hwnd": 349525},
        hit=hit, target_pid=target_pid,
    )

    cli_verdict = _cli_verdict(cli_result)
    mcp_verdict = _mcp_verdict(mcp_payload)
    assert cli_verdict == mcp_verdict == (False, "CLICK_WRONG_WINDOW")


def test_cli_and_mcp_agree_on_success_verdict():
    """Contract: a same-process landing is a success on BOTH surfaces."""
    hit = (349525, "Target App", 111)
    target_pid = 111

    cli_result = _invoke_cli_click(
        ["--coords", "500", "300", "--hwnd", "349525"],
        hit=hit, target_pid=target_pid,
    )
    mcp_payload, _ = _call_mcp_click(
        {"x": 500, "y": 300, "hwnd": 349525},
        hit=hit, target_pid=target_pid,
    )

    assert _cli_verdict(cli_result) == _mcp_verdict(mcp_payload) == (True, None)
