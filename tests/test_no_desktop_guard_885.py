"""Regression matrix for the NO_DESKTOP_SESSION silent-failure cluster (#885).

Root cause: a set of CLI enumeration/read commands (``app windows``,
``dialog detect``, ``taskbar list``, ``tray list``, ``wait --gone``) and MCP
read tools (``capture_screen``, ``list_windows``, ``list_apps``,
``app_inspect``, ``capture_window``, ``list_monitors``) reached the backend
without the desktop-session pre-flight check.  In a NO_DESKTOP_SESSION
environment they returned fabricated success — empty arrays, all-black PNGs,
stale window lists — instead of failing loudly.

This module mocks the no-desktop-session condition and asserts every command
above fails loudly:

* CLI: ``NO_DESKTOP_SESSION`` envelope (``-j``) / clear message, exit code 1.
* MCP: the tool raises (transport flags ``isError:true``), carrying the
  ``NO_DESKTOP_SESSION`` signal — it never returns fabricated data.

Session-independent commands (``--version``, ``--help``) are explicitly
allow-listed and must still succeed.

Closes #885 / #868 / #875 / #878 / #883 / #893.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.errors import NoDesktopSessionError


@pytest.fixture
def no_desktop():
    """Force ``_check_desktop_session`` to raise as if no desktop is present.

    Patched at the canonical definition site so both the CLI guard
    (``naturo.cli.core._common``) and the MCP guard (``naturo.mcp_server``)
    pick up the failure through their lazy imports.
    """
    with patch(
        "naturo.cli.interaction._check_desktop_session",
        side_effect=NoDesktopSessionError(),
    ):
        yield


# ── CLI surface ──────────────────────────────────────────────────────────────

# (command-line argv) tuples that MUST fail loudly with NO_DESKTOP_SESSION.
# Each is run both plain and with -j to lock down both output paths.
_CLI_GUARDED = [
    pytest.param(["app", "windows"], id="app-windows"),
    pytest.param(["dialog", "detect"], id="dialog-detect"),
    pytest.param(["taskbar", "list"], id="taskbar-list"),
    pytest.param(["tray", "list"], id="tray-list"),
    pytest.param(["wait", "--gone", "Dialog:Loading", "--timeout", "1"], id="wait-gone"),
    pytest.param(["wait", "--element", "Button:Save", "--timeout", "1"], id="wait-element"),
    pytest.param(["wait", "--window", "Notepad", "--timeout", "1"], id="wait-window"),
]


def _run_cli(argv):
    """Invoke the naturo CLI with *argv* and return the Click result."""
    from naturo.cli import main
    return CliRunner().invoke(main, argv, catch_exceptions=False)


@pytest.mark.parametrize("argv", _CLI_GUARDED)
def test_cli_command_fails_loudly_json(no_desktop, argv):
    """With -j, each guarded command emits a NO_DESKTOP_SESSION envelope, exit 1."""
    result = _run_cli([*argv, "-j"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload.get("success") is False
    # Error code lives at the top level or under an "error" object depending on
    # the envelope helper — accept either, but it must be NO_DESKTOP_SESSION.
    code = payload.get("code") or payload.get("error", {}).get("code")
    assert code == "NO_DESKTOP_SESSION", payload


@pytest.mark.parametrize("argv", _CLI_GUARDED)
def test_cli_command_fails_loudly_plain(no_desktop, argv):
    """Without -j, each guarded command exits non-zero (no fabricated success)."""
    result = _run_cli(argv)
    assert result.exit_code != 0, result.output


def test_cli_app_windows_does_not_leak_window_list(no_desktop):
    """Regression for #878: app windows -j must not emit a real window list."""
    backend = MagicMock()
    backend.list_windows.return_value = [MagicMock(handle=1, title="leak")]
    with patch("naturo.backends.base.get_backend", return_value=backend):
        result = _run_cli(["app", "windows", "-j"])
    assert result.exit_code == 1
    backend.list_windows.assert_not_called()


# ── CLI allow-list (session-independent) ─────────────────────────────────────

@pytest.mark.parametrize("argv", [["--version"], ["--help"]])
def test_cli_session_independent_commands_succeed(no_desktop, argv):
    """--version / --help never touch the desktop and must still succeed."""
    result = _run_cli(argv)
    assert result.exit_code == 0, result.output


# ── MCP surface ──────────────────────────────────────────────────────────────

mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:  # pragma: no cover - mcp optional
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


# (tool_name, arguments) for every read tool that obtains its backend through
# the guarded _get_backend() and previously leaked data in NO_DESKTOP_SESSION.
_MCP_GUARDED = [
    pytest.param("capture_screen", {}, id="capture_screen"),
    pytest.param("capture_window", {}, id="capture_window"),
    pytest.param("list_monitors", {}, id="list_monitors"),
    pytest.param("list_windows", {}, id="list_windows"),
    pytest.param("list_apps", {}, id="list_apps"),
    pytest.param("app_inspect", {"name": "explorer"}, id="app_inspect"),
]


def _call_mcp_tool(server, tool_name, arguments):
    """Drive an MCP tool to completion, returning its result or raising."""
    async def _run():
        return await server.call_tool(tool_name, arguments)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


@pytest.mark.parametrize("tool_name,arguments", _MCP_GUARDED)
def test_mcp_tool_fails_loudly(no_desktop, tool_name, arguments):
    """Each read tool raises (→ isError:true) and never returns fabricated data.

    The backend is mocked to return plausible data; the guard must trip before
    any backend method runs, so no fabricated payload can reach the caller.
    """
    backend = MagicMock()
    with patch("naturo.mcp_server.get_backend", return_value=backend):
        server = create_server()
        with pytest.raises(Exception) as exc_info:
            _call_mcp_tool(server, tool_name, arguments)
    # The loud-failure signal must mention NO_DESKTOP_SESSION so an agent can
    # branch on it rather than a generic transport error.
    assert "NO_DESKTOP_SESSION" in str(exc_info.value) or "desktop session" in str(
        exc_info.value
    ).lower()
    # No backend enumeration ran — wrong data was structurally impossible.
    backend.list_windows.assert_not_called()
    backend.list_apps.assert_not_called()
    backend.capture_screen.assert_not_called()
