"""Tests for the opt-in input-content safety guard (naturo.safety, #960/#972).

The guard refuses to inject shell-command-like keystrokes when it is active, so
a focus race in an unattended QA loop cannot deliver a destructive fragment
(e.g. ``$(rm -rf /)``) to a terminal.  It activates on **either** of two
independent signals (#972): the ``NATURO_SAFE_INPUT=1`` environment variable or
a sentinel lock file at ``~/.naturo/safe-input.lock``.  The file-based signal is
the robust primary because it survives across process boundaries with no
env-inheritance dependency.  Normal users (neither signal present) must be
completely unaffected.

All tests are pure-Python (no desktop, no DLL, no real keystrokes) and run on
Linux CI; the sentinel filesystem is mocked via a tmp HOME.
"""
from __future__ import annotations

import json
from pathlib import Path
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


class TestSentinelFileGating:
    """The sentinel lock file activates the guard independently of the env var.

    This is the #972 robustness fix: the env var alone proved fragile because it
    must be inherited by every process in the injection chain.  The lock file is
    probed from disk on each call, so it works regardless of how ``naturo`` was
    spawned.  The filesystem is mocked via a tmp HOME so no real file under the
    developer's ``~/.naturo`` is touched.
    """

    @staticmethod
    def _home(monkeypatch, tmp_path):
        """Point ``Path.home()`` at ``tmp_path`` and clear the guard env var."""
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
        monkeypatch.delenv(SAFE_INPUT_ENV, raising=False)
        return tmp_path / ".naturo" / "safe-input.lock"

    def test_lock_path_lives_under_dot_naturo(self, monkeypatch, tmp_path):
        from naturo.safety import _safe_input_lock_path

        self._home(monkeypatch, tmp_path)
        assert _safe_input_lock_path() == tmp_path / ".naturo" / "safe-input.lock"

    def test_active_when_sentinel_exists_and_env_unset(self, monkeypatch, tmp_path):
        """The exact #972 scenario: env var UNSET but the sentinel file exists."""
        lock = self._home(monkeypatch, tmp_path)
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.touch()

        assert SAFE_INPUT_ENV not in __import__("os").environ
        assert is_safe_input_enabled() is True
        # And it actually blocks the near-miss payload from the incident.
        assert unsafe_input_reason("$(rm -rf /)") is not None

    def test_inactive_when_neither_env_nor_sentinel(self, monkeypatch, tmp_path):
        self._home(monkeypatch, tmp_path)  # tmp HOME has no .naturo dir/lock

        assert is_safe_input_enabled() is False
        # Dangerous content passes untouched — normal users are unaffected.
        assert unsafe_input_reason("$(rm -rf /)") is None

    def test_benign_passes_even_when_sentinel_present(self, monkeypatch, tmp_path):
        lock = self._home(monkeypatch, tmp_path)
        lock.parent.mkdir(parents=True, exist_ok=True)
        lock.touch()

        assert is_safe_input_enabled() is True
        assert unsafe_input_reason("QA_PROBE") is None

    def test_env_alone_still_works_without_sentinel(self, monkeypatch, tmp_path):
        """Env-var fallback is preserved even when no sentinel file exists."""
        self._home(monkeypatch, tmp_path)
        monkeypatch.setenv(SAFE_INPUT_ENV, "1")

        assert is_safe_input_enabled() is True
        assert unsafe_input_reason("$(rm -rf /)") is not None


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

    # ── #1160: the clipboard-only `--paste` path must honor the guard too ──

    def test_paste_with_text_blocks_dangerous(self):
        """`type "<dangerous>" --paste` is blocked (text-argument paste path)."""
        from unittest.mock import MagicMock

        backend = MagicMock()
        with _enabled():
            result = self._invoke(["test$(rm -rf /)", "--paste", "-j"], backend)
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["error"]["code"] == "UNSAFE_INPUT_BLOCKED"
        backend.hotkey.assert_not_called()
        backend.clipboard_set.assert_not_called()

    def test_bare_paste_blocks_dangerous_clipboard(self):
        """(#1160) bare `type --paste` reads the clipboard and refuses to
        Ctrl+V destructive content when the guard is armed — the bypass the
        issue reported."""
        from unittest.mock import MagicMock

        backend = MagicMock()
        backend.clipboard_get.return_value = "$(rm -rf /)"
        with _enabled():
            result = self._invoke(["--paste", "-j"], backend)
        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["success"] is False
        assert payload["error"]["code"] == "UNSAFE_INPUT_BLOCKED"
        # Nothing was pasted.
        backend.hotkey.assert_not_called()

    def test_bare_paste_allows_benign_clipboard(self):
        """A benign clipboard still pastes normally under the armed guard."""
        from unittest.mock import MagicMock

        backend = MagicMock()
        backend.clipboard_get.return_value = "hello world"
        with _enabled():
            result = self._invoke(["--paste", "-j"], backend)
        assert result.exit_code == 0
        backend.hotkey.assert_any_call("ctrl", "v")

    def test_bare_paste_unaffected_when_guard_off(self):
        """Guard off: bare paste injects whatever is on the clipboard, as before
        (and does not even need to read it for the guard)."""
        from unittest.mock import MagicMock

        backend = MagicMock()
        backend.clipboard_get.return_value = "$(rm -rf /)"
        with mock.patch.dict("os.environ", {}, clear=True):
            result = self._invoke(["--paste", "-j"], backend)
        assert result.exit_code == 0
        backend.hotkey.assert_any_call("ctrl", "v")


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
        # #1219/#1239: type_text prefers ValuePattern → clipboard paste before the
        # keystroke rung. Steer to keystroke (no writable ValuePattern, no paste)
        # so backend.type_text is the delivery proof that the content was NOT
        # blocked when NATURO_SAFE_INPUT is unset.
        backend.set_focused_element_value.return_value = False
        backend.clipboard_set.side_effect = RuntimeError("no clipboard")
        with self._server(backend):
            server = create_server()
            with mock.patch.dict("os.environ", {}, clear=True):
                result = self._call(server, {"text": "test$(rm -rf /)"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        backend.type_text.assert_called_once()


class TestMcpPasteHelperGuard:
    """(#1160) The MCP clipboard-paste helper honors the guard at the paste
    boundary itself — belt-and-suspenders behind ``type_text``'s up-front check,
    so no future caller can reintroduce a paste bypass."""

    def test_paste_helper_refuses_dangerous_when_enabled(self):
        from unittest.mock import MagicMock

        from naturo.mcp._input import _paste_text

        backend = MagicMock()
        with _enabled():
            delivered = _paste_text(backend, "$(rm -rf /)")
        assert delivered is False
        backend.clipboard_set.assert_not_called()
        backend.hotkey.assert_not_called()

    def test_paste_helper_delivers_benign_when_enabled(self):
        from unittest.mock import MagicMock

        from naturo.mcp._input import _paste_text

        backend = MagicMock()
        backend.clipboard_get.return_value = "prior"
        with _enabled():
            delivered = _paste_text(backend, "hello world")
        assert delivered is True
        backend.hotkey.assert_any_call("ctrl", "v")

    def test_paste_helper_delivers_dangerous_when_guard_off(self):
        from unittest.mock import MagicMock

        from naturo.mcp._input import _paste_text

        backend = MagicMock()
        backend.clipboard_get.return_value = "prior"
        with mock.patch.dict("os.environ", {}, clear=True):
            delivered = _paste_text(backend, "$(rm -rf /)")
        assert delivered is True
        backend.hotkey.assert_any_call("ctrl", "v")
