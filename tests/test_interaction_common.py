"""Tests for naturo.cli.interaction._common — shared interaction helpers."""
from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import click
import pytest

from naturo.cli.interaction._common import (
    _check_desktop_session,
    _json_err,
    _json_ok,
    _VERIFICATION_KEYS,
)


# ── _json_ok ─────────────────────────────────────


class TestJsonOk:
    """Tests for _json_ok() output helper."""

    def test_json_mode_wraps_data(self):
        out = []
        with patch("naturo.cli.interaction._common.click.echo", side_effect=out.append):
            _json_ok({"action": "pressed", "key": "enter"}, json_output=True)
        parsed = json.loads(out[0])
        assert parsed["success"] is True
        assert parsed["data"]["action"] == "pressed"

    def test_text_mode_prints_key_value(self):
        out = []
        with patch("naturo.cli.interaction._common.click.echo", side_effect=out.append):
            _json_ok({"action": "pressed", "key": "enter"}, json_output=False)
        assert "action: pressed" in out
        assert "key: enter" in out

    def test_text_mode_hides_verification_keys(self):
        out = []
        data = {
            "action": "pressed",
            "verified": True,
            "verification_detail": "focus changed",
            "verification_method": "focus",
        }
        with patch("naturo.cli.interaction._common.click.echo", side_effect=out.append):
            _json_ok(data, json_output=False)
        joined = " ".join(str(o) for o in out)
        assert "action: pressed" in joined
        assert "verified" not in joined
        assert "verification_detail" not in joined

    def test_json_mode_keeps_verification_keys(self):
        out = []
        data = {
            "action": "pressed",
            "verified": True,
            "verification_detail": "focus changed",
        }
        with patch("naturo.cli.interaction._common.click.echo", side_effect=out.append):
            _json_ok(data, json_output=True)
        parsed = json.loads(out[0])
        assert parsed["data"]["verified"] is True
        assert parsed["data"]["verification_detail"] == "focus changed"


# ── _json_err ────────────────────────────────────


class TestJsonErr:
    """Tests for _json_err() error helper."""

    def test_json_mode_outputs_error_json(self):
        out = []
        with patch("naturo.cli.interaction._common.click.echo", side_effect=out.append):
            with pytest.raises(SystemExit) as exc_info:
                _json_err("something broke", json_output=True, code="TEST_ERROR")
            assert exc_info.value.code == 1
        # Should contain JSON with error info
        assert "TEST_ERROR" in out[0] or "something broke" in out[0]

    def test_text_mode_outputs_to_stderr(self):
        with patch("naturo.cli.interaction._common.click.echo") as mock_echo:
            with pytest.raises(SystemExit) as exc_info:
                _json_err("bad input", json_output=False)
            assert exc_info.value.code == 1
            mock_echo.assert_called_once_with("Error: bad input", err=True)

    def test_custom_exit_code(self):
        with patch("naturo.cli.interaction._common.click.echo"):
            with pytest.raises(SystemExit) as exc_info:
                _json_err("fail", json_output=True, exit_code=2)
            assert exc_info.value.code == 2


# ── _check_desktop_session ───────────────────────


class TestCheckDesktopSession:
    """Tests for _check_desktop_session() pre-flight check."""

    @patch("platform.system", return_value="Linux")
    def test_non_windows_is_noop(self, _mock):
        _check_desktop_session()  # No exception on non-Windows

    @patch("platform.system", return_value="Windows")
    @patch.dict(os.environ, {"SESSIONNAME": "Console"}, clear=False)
    def test_console_session_passes(self, _mock):
        _check_desktop_session()

    @patch("platform.system", return_value="Windows")
    @patch.dict(os.environ, {"SESSIONNAME": "RDP-Tcp#0"}, clear=False)
    def test_rdp_session_passes(self, _mock):
        _check_desktop_session()

    @patch("platform.system", return_value="Windows")
    @patch.dict(os.environ, {"SESSIONNAME": "Services"}, clear=False)
    def test_services_session_raises(self, _mock):
        from naturo.errors import NoDesktopSessionError
        with pytest.raises(NoDesktopSessionError):
            _check_desktop_session()

    @patch("platform.system", return_value="Windows")
    @patch.dict(os.environ, {"SESSIONNAME": "ICA-tcp#1"}, clear=False)
    def test_citrix_session_passes(self, _mock):
        _check_desktop_session()

    @patch("naturo.cli.interaction._common._is_current_session_interactive", return_value=True)
    @patch("platform.system", return_value="Windows")
    @patch.dict(os.environ, {"SESSIONNAME": ""}, clear=False)
    def test_empty_sessionname_wts_interactive_passes(self, _mock_plat, _mock_wts):
        _check_desktop_session()

    @patch("naturo.cli.interaction._common._is_current_session_interactive", return_value=False)
    @patch("platform.system", return_value="Windows")
    @patch.dict(os.environ, {"SESSIONNAME": ""}, clear=False)
    def test_empty_sessionname_not_interactive_raises(self, _mock_plat, _mock_wts):
        from naturo.errors import NoDesktopSessionError
        # Mock subprocess to return no explorer
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="")
            with pytest.raises(NoDesktopSessionError):
                _check_desktop_session()


# ── _VERIFICATION_KEYS ───────────────────────────


class TestVerificationKeys:
    """Verify the constant set is correctly defined."""

    def test_contains_expected_keys(self):
        assert "verified" in _VERIFICATION_KEYS
        assert "verification_detail" in _VERIFICATION_KEYS
        assert "verification_method" in _VERIFICATION_KEYS
        assert "verification_ms" in _VERIFICATION_KEYS
        assert "verification_error" in _VERIFICATION_KEYS

    def test_is_frozen(self):
        assert isinstance(_VERIFICATION_KEYS, frozenset)
