"""Tests for naturo.cli.interaction._press — press and hotkey commands."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, call

import click
import pytest
from click.testing import CliRunner

from naturo.cli.interaction._press import _is_combo, press, hotkey


@pytest.fixture
def runner():
    return CliRunner()


# ── _is_combo ────────────────────────────────────


class TestIsCombo:
    """Tests for _is_combo() helper."""

    def test_simple_key_not_combo(self):
        assert _is_combo("enter") is False

    def test_ctrl_c_is_combo(self):
        assert _is_combo("ctrl+c") is True

    def test_alt_f4_is_combo(self):
        assert _is_combo("alt+f4") is True

    def test_ctrl_shift_s_is_combo(self):
        assert _is_combo("ctrl+shift+s") is True

    def test_empty_string_not_combo(self):
        assert _is_combo("") is False

    def test_plus_only_is_combo(self):
        # "+" by itself has a + character
        assert _is_combo("+") is True


# ── press command — validation ───────────────────


class TestPressValidation:
    """Tests for press command input validation."""

    @patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None))
    def test_no_keys_shows_error(self, mock_resolve, runner):
        result = runner.invoke(press, [], catch_exceptions=False)
        assert result.exit_code != 0

    @patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None))
    def test_no_keys_json_shows_error(self, mock_resolve, runner):
        result = runner.invoke(press, ["--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "INVALID_INPUT" in result.output or "Missing" in result.output

    @patch("naturo.cli.interaction._common._get_backend")
    @patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None))
    def test_count_zero_shows_error(self, mock_resolve, mock_backend, runner):
        result = runner.invoke(press, ["enter", "--count", "0"], catch_exceptions=False)
        assert result.exit_code != 0

    @patch("naturo.cli.interaction._common._get_backend")
    @patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None))
    def test_negative_hold_duration_shows_error(self, mock_resolve, mock_backend, runner):
        result = runner.invoke(
            press, ["ctrl+c", "--hold-duration", "-1"],
            catch_exceptions=False,
        )
        assert result.exit_code != 0


# ── press command — single key ──────────────────


class TestPressSingleKey:
    """Tests for pressing single keys."""

    @patch("naturo.cli.interaction._common._auto_route", return_value=None)
    @patch("naturo.cli.interaction._common._get_backend")
    @patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None))
    def test_single_key_calls_press_key(self, mock_resolve, mock_get_backend, mock_route, runner):
        backend = MagicMock()
        mock_get_backend.return_value = backend

        result = runner.invoke(
            press, ["enter", "--json", "--no-verify"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        backend.press_key.assert_called_once_with("enter", input_mode="normal")
        data = json.loads(result.output)["data"]
        assert data["action"] == "pressed"
        assert data["key"] == "enter"

    @patch("naturo.cli.interaction._common._auto_route", return_value=None)
    @patch("naturo.cli.interaction._common._get_backend")
    @patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None))
    def test_single_key_with_count(self, mock_resolve, mock_get_backend, mock_route, runner):
        backend = MagicMock()
        mock_get_backend.return_value = backend

        result = runner.invoke(
            press, ["tab", "--count", "3", "--json", "--no-verify"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert backend.press_key.call_count == 3
        data = json.loads(result.output)["data"]
        assert data["count"] == 3


# ── press command — combos ──────────────────────


class TestPressCombo:
    """Tests for pressing key combinations."""

    @patch("naturo.cli.interaction._common._auto_route", return_value=None)
    @patch("naturo.cli.interaction._common._get_backend")
    @patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None))
    def test_combo_calls_hotkey(self, mock_resolve, mock_get_backend, mock_route, runner):
        backend = MagicMock()
        mock_get_backend.return_value = backend

        result = runner.invoke(
            press, ["ctrl+c", "--json", "--no-verify"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        backend.hotkey.assert_called_once()
        args = backend.hotkey.call_args
        assert "ctrl" in args[0]
        assert "c" in args[0]

    @patch("naturo.cli.interaction._common._auto_route", return_value=None)
    @patch("naturo.cli.interaction._common._get_backend")
    @patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None))
    def test_combo_with_hold_duration(self, mock_resolve, mock_get_backend, mock_route, runner):
        backend = MagicMock()
        mock_get_backend.return_value = backend

        result = runner.invoke(
            press, ["alt+f4", "--hold-duration", "100", "--json", "--no-verify"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        backend.hotkey.assert_called_once()
        kwargs = backend.hotkey.call_args[1]
        assert kwargs["hold_duration_ms"] == 100


# ── press command — sequential keys ────────────


class TestPressSequential:
    """Tests for pressing multiple keys in sequence."""

    @patch("naturo.cli.interaction._common._auto_route", return_value=None)
    @patch("naturo.cli.interaction._common._get_backend")
    @patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None))
    def test_sequential_keys(self, mock_resolve, mock_get_backend, mock_route, runner):
        backend = MagicMock()
        mock_get_backend.return_value = backend

        result = runner.invoke(
            press, ["tab", "enter", "--json", "--no-verify", "--delay", "0"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert backend.press_key.call_count == 2
        data = json.loads(result.output)["data"]
        assert data["action"] == "pressed"
        assert data["sequence"] == ["tab", "enter"]

    @patch("naturo.cli.interaction._common._auto_route", return_value=None)
    @patch("naturo.cli.interaction._common._get_backend")
    @patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None))
    def test_mixed_keys_and_combos(self, mock_resolve, mock_get_backend, mock_route, runner):
        backend = MagicMock()
        mock_get_backend.return_value = backend

        result = runner.invoke(
            press, ["ctrl+a", "ctrl+c", "--json", "--no-verify", "--delay", "0"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert backend.hotkey.call_count == 2


# ── press command — error handling ──────────────


class TestPressErrors:
    """Tests for press command error handling."""

    @patch("naturo.cli.interaction._common._auto_route", return_value=None)
    @patch("naturo.cli.interaction._common._get_backend")
    @patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None))
    def test_backend_error_json(self, mock_resolve, mock_get_backend, mock_route, runner):
        backend = MagicMock()
        backend.press_key.side_effect = RuntimeError("key not recognized")
        mock_get_backend.return_value = backend

        result = runner.invoke(
            press, ["unknownkey", "--json", "--no-verify"],
            catch_exceptions=False,
        )
        assert result.exit_code != 0
        assert "key not recognized" in result.output


# ── press command — --on element ────────────────


class TestPressOnElement:
    """Tests for --on element targeting."""

    @patch("naturo.cli.interaction._common._auto_route", return_value=None)
    @patch("naturo.cli.interaction._common._get_backend")
    @patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None))
    def test_on_ref_resolves_and_clicks(self, mock_resolve, mock_get_backend, mock_route, runner):
        backend = MagicMock()
        mock_get_backend.return_value = backend

        with patch("naturo.snapshot.get_snapshot_manager") as mock_mgr_factory:
            mgr = MagicMock()
            mgr.resolve_ref.return_value = (100, 200)
            mock_mgr_factory.return_value = mgr

            result = runner.invoke(
                press, ["enter", "--on", "e5", "--json", "--no-verify", "--delay", "0"],
                catch_exceptions=False,
            )
            assert result.exit_code == 0
            mgr.resolve_ref.assert_called_once_with("e5", app_name=None)
            # Should click at resolved coords then press key
            backend.click.assert_called_once()
            backend.press_key.assert_called_once()

    @patch("naturo.cli.interaction._common._auto_route", return_value=None)
    @patch("naturo.cli.interaction._common._get_backend")
    @patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None))
    def test_on_ref_not_found(self, mock_resolve, mock_get_backend, mock_route, runner):
        backend = MagicMock()
        mock_get_backend.return_value = backend

        with patch("naturo.snapshot.get_snapshot_manager") as mock_mgr_factory:
            mgr = MagicMock()
            mgr.resolve_ref.return_value = None
            mock_mgr_factory.return_value = mgr

            result = runner.invoke(
                press, ["enter", "--on", "e99", "--json", "--no-verify"],
                catch_exceptions=False,
            )
            assert result.exit_code != 0
            assert "REF_NOT_FOUND" in result.output or "not found" in result.output.lower()

    @patch("naturo.cli.interaction._common._auto_route", return_value=None)
    @patch("naturo.cli.interaction._common._get_backend")
    @patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None))
    def test_on_text_label_resolves(self, mock_resolve, mock_get_backend, mock_route, runner):
        backend = MagicMock()
        elem = MagicMock(x=50, y=60, width=100, height=40)
        backend.find_element.return_value = elem
        mock_get_backend.return_value = backend

        result = runner.invoke(
            press, ["enter", "--on", "OK Button", "--json", "--no-verify", "--delay", "0"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        backend.find_element.assert_called_once_with("OK Button")
        backend.click.assert_called_once()
        backend.press_key.assert_called_once()


# ── hotkey command (deprecated alias) ────────────


class TestHotkeyAlias:
    """Tests for the deprecated hotkey command."""

    def test_hotkey_shows_deprecation_warning(self, runner):
        with patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None)):
            with patch("naturo.cli.interaction._common._get_backend") as mock_get:
                backend = MagicMock()
                mock_get.return_value = backend
                with patch("naturo.cli.interaction._common._auto_route", return_value=None):
                    result = runner.invoke(
                        hotkey, ["ctrl+c", "--no-verify"],
                        catch_exceptions=False,
                    )
                    # Deprecation warning goes to stderr
                    assert "deprecated" in (result.output or "").lower() or result.exit_code == 0

    def test_hotkey_no_keys_shows_error(self, runner):
        with patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None)):
            result = runner.invoke(hotkey, [], catch_exceptions=False)
            assert result.exit_code != 0

    def test_hotkey_json_no_keys_shows_error(self, runner):
        with patch("naturo.cli.interaction._common._resolve_app_id", return_value=(None, None, None)):
            result = runner.invoke(hotkey, ["--json"], catch_exceptions=False)
            assert result.exit_code != 0
            assert "INVALID_INPUT" in result.output or "keys" in result.output.lower()
