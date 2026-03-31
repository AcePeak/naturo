"""Tests for naturo.cli.core._common — shared CLI core helpers."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import click
import pytest

from naturo.cli.core._common import (
    _get_backend,
    _platform_error_msg,
    _platform_supports_gui,
)


# ── _get_backend ─────────────────────────────────


class TestGetBackend:
    """Tests for _get_backend()."""

    @patch("naturo.cli.core._common._json_error_str")
    @patch("naturo.cli.interaction._check_desktop_session")
    def test_desktop_check_fails_plain_raises_usage_error(
        self, mock_check, mock_json_err
    ):
        mock_check.side_effect = RuntimeError("no desktop")
        with pytest.raises(click.UsageError, match="no desktop"):
            _get_backend(json_output=False)

    @patch("naturo.cli.core._common._json_error_str", return_value='{"error": "x"}')
    @patch("naturo.cli.interaction._check_desktop_session")
    def test_desktop_check_fails_json_exits(self, mock_check, mock_json_err):
        mock_check.side_effect = RuntimeError("no desktop")
        with pytest.raises(SystemExit) as exc_info:
            _get_backend(json_output=True)
        assert exc_info.value.code == 1
        mock_json_err.assert_called_once_with("NO_DESKTOP_SESSION", "no desktop")

    @patch("naturo.backends.base.get_backend")
    @patch("naturo.cli.interaction._check_desktop_session")
    def test_success_returns_backend(self, mock_check, mock_get):
        sentinel = MagicMock(name="backend")
        mock_get.return_value = sentinel
        result = _get_backend(json_output=False)
        assert result is sentinel
        mock_check.assert_called_once()
        mock_get.assert_called_once()

    @patch("naturo.backends.base.get_backend")
    @patch("naturo.cli.interaction._check_desktop_session")
    def test_success_json_mode_returns_backend(self, mock_check, mock_get):
        sentinel = MagicMock(name="backend")
        mock_get.return_value = sentinel
        result = _get_backend(json_output=True)
        assert result is sentinel


# ── _platform_supports_gui ───────────────────────


class TestPlatformSupportsGui:
    """Tests for _platform_supports_gui()."""

    @patch("naturo.cli.core._common.platform.system", return_value="Windows")
    def test_windows_always_true(self, _mock):
        assert _platform_supports_gui() is True

    @patch("shutil.which", return_value="/usr/local/bin/peekaboo")
    @patch("naturo.cli.core._common.platform.system", return_value="Darwin")
    def test_darwin_with_peekaboo(self, _mock_sys, _mock_which):
        assert _platform_supports_gui() is True

    @patch("shutil.which", return_value=None)
    @patch("naturo.cli.core._common.platform.system", return_value="Darwin")
    def test_darwin_without_peekaboo(self, _mock_sys, _mock_which):
        assert _platform_supports_gui() is False

    @patch("naturo.cli.core._common.platform.system", return_value="Linux")
    def test_linux_returns_false(self, _mock):
        assert _platform_supports_gui() is False

    @patch("naturo.cli.core._common.platform.system", return_value="FreeBSD")
    def test_unknown_os_returns_false(self, _mock):
        assert _platform_supports_gui() is False


# ── _platform_error_msg ──────────────────────────


class TestPlatformErrorMsg:
    """Tests for _platform_error_msg()."""

    @patch("naturo.cli.core._common.platform.system", return_value="Darwin")
    def test_darwin_message(self, _mock):
        msg = _platform_error_msg("Screen capture")
        assert "Peekaboo" in msg
        assert "Screen capture" in msg
        assert "peekaboo" in msg.lower()

    @patch("naturo.cli.core._common.platform.system", return_value="Linux")
    def test_linux_message(self, _mock):
        msg = _platform_error_msg("Screen capture")
        assert "not yet supported on Linux" in msg
        assert "Screen capture" in msg

    @patch("naturo.cli.core._common.platform.system", return_value="FreeBSD")
    def test_unknown_os_message(self, _mock):
        msg = _platform_error_msg("UI inspection")
        assert "not supported on FreeBSD" in msg
        assert "UI inspection" in msg
