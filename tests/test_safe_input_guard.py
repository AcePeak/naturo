"""Tests for the opt-in input-content safety guard (naturo.safety, #960).

The guard refuses to inject shell-command-like keystrokes when
``NATURO_SAFE_INPUT=1`` is set, so a focus race in an unattended QA loop cannot
deliver a destructive fragment (e.g. ``$(rm -rf /)``) to a terminal.  Normal
users (env unset) must be completely unaffected.

All tests are pure-Python (no desktop, no DLL) and run on Linux CI.
"""
from __future__ import annotations

import json
from unittest import mock

import pytest

from naturo.safety import (
    SAFE_INPUT_ENV,
    UNSAFE_INPUT_CODE,
    is_safe_input_enabled,
    unsafe_input_reason,
)


def _enabled():
    return mock.patch.dict("os.environ", {SAFE_INPUT_ENV: "1"})


class TestEnvGating:

    def test_disabled_when_unset(self):
        with mock.patch.dict("os.environ", {}, clear=True):
            assert is_safe_input_enabled() is False
            # Even an obviously dangerous string passes when the guard is off.
            assert unsafe_input_reason("test$(rm -rf /)") is None

    def test_disabled_when_not_exactly_one(self):
        for value in ("0", "true", "yes", "2", ""):
            with mock.patch.dict("os.environ", {SAFE_INPUT_ENV: value}, clear=True):
                assert is_safe_input_enabled() is False
                assert unsafe_input_reason("rm -rf /") is None

    def test_enabled_when_exactly_one(self):
        with _enabled():
            assert is_safe_input_enabled() is True


class TestBlocksDangerousContent:

    @pytest.mark.parametrize(
        "text",
        [
            "test$(rm -rf /)",          # the exact near-miss from the report
            "echo `whoami`",            # backtick command substitution
            "foo && rm bar",            # logical AND + rm
            "a || b",                   # logical OR
            "first; second",            # command separator
            "cat x | grep y",           # pipe
            "echo hi > file",           # output redirect
            "cmd < input",              # input redirect
            "rm important.txt",         # rm verb
            "rmdir folder",             # rmdir verb
            "del C:\\file",             # del verb
            "format C:",                # format verb
            "shutdown /s",              # shutdown verb
            "sudo reboot",              # sudo verb
            "RM -RF /",                 # case-insensitive
        ],
    )
    def test_dangerous_blocked_when_enabled(self, text):
        with _enabled():
            reason = unsafe_input_reason(text)
            assert reason is not None, f"expected {text!r} to be blocked"
            assert isinstance(reason, str) and reason


class TestAllowsBenignContent:

    @pytest.mark.parametrize(
        "text",
        [
            "QA_PROBE",
            "Hello World",
            "The quick brown fox.",
            "warm welcome and a delete-free paragraph",  # substrings, not commands
            "reformatted the document",                  # 'format' as substring
            "user@example.com",
            "Price: 100 dollars",
            "naturo automates Windows",
            "",
            "12345",
        ],
    )
    def test_benign_allowed_when_enabled(self, text):
        with _enabled():
            assert unsafe_input_reason(text) is None

    def test_none_is_safe(self):
        with _enabled():
            assert unsafe_input_reason(None) is None


def test_code_constant_value():
    """The error code is the stable contract QA/agents key off."""
    assert UNSAFE_INPUT_CODE == "UNSAFE_INPUT_BLOCKED"


# ── Integration: CLI `naturo type` ───────────────────────────────────


class TestCliTypeGuard:

    def _invoke(self, args, backend):
        from click.testing import CliRunner

        from naturo.cli.interaction._type import type_cmd

        with mock.patch(
            "naturo.cli.interaction._common._resolve_app_id",
            return_value=(None, None, None),
        ), mock.patch(
            "naturo.cli.interaction._common._get_backend", return_value=backend
        ), mock.patch(
            "naturo.cli.interaction._common._auto_route", return_value={}
        ):
            return CliRunner().invoke(type_cmd, args, catch_exceptions=False)

    def test_blocks_dangerous_when_enabled(self):
        from unittest.mock import MagicMock

        backend = MagicMock()
        with _enabled():
            result = self._invoke(["test$(rm -rf /)", "-j"], backend)
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["success"] is False
        assert payload["error"]["code"] == "UNSAFE_INPUT_BLOCKED"
        # Nothing was injected.
        backend.type_text.assert_not_called()

    def test_allows_dangerous_when_disabled(self):
        from unittest.mock import MagicMock

        backend = MagicMock()
        with mock.patch.dict("os.environ", {}, clear=True):
            result = self._invoke(["test$(rm -rf /)", "-j"], backend)
        assert result.exit_code == 0
        backend.type_text.assert_called_once()

    def test_allows_benign_when_enabled(self):
        from unittest.mock import MagicMock

        backend = MagicMock()
        with _enabled():
            result = self._invoke(["QA_PROBE", "-j"], backend)
        assert result.exit_code == 0
        backend.type_text.assert_called_once()


# ── Integration: MCP `type` tool ─────────────────────────────────────

mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:  # pragma: no cover - mcp optional on some lanes
    mcp_available = False


@pytest.mark.skipif(not mcp_available, reason="mcp package not installed")
class TestMcpTypeGuard:

    def _call(self, server, arguments):
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(server.call_tool("type_text", arguments))
        finally:
            loop.close()

    def _server(self, backend):
        return mock.patch("naturo.mcp_server.get_backend", return_value=backend)

    def test_blocks_dangerous_when_enabled(self):
        from unittest.mock import MagicMock

        backend = MagicMock()
        with self._server(backend):
            server = create_server()
            with _enabled():
                result = self._call(server, {"text": "test$(rm -rf /)"})
        data = json.loads(result[0].text)
        assert data["success"] is False
        assert data["error"]["code"] == "UNSAFE_INPUT_BLOCKED"
        backend.type_text.assert_not_called()

    def test_allows_dangerous_when_disabled(self):
        from unittest.mock import MagicMock

        backend = MagicMock()
        with self._server(backend):
            server = create_server()
            with mock.patch.dict("os.environ", {}, clear=True):
                result = self._call(server, {"text": "test$(rm -rf /)"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        backend.type_text.assert_called_once()
