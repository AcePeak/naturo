"""Tests for --method override flag on action commands (#34).

Validates that all action commands accept the --method flag,
validate its values, and pass the method through to routing logic.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from naturo.cli.interaction import (
    VALID_METHODS,
    _method_option,
    _validate_method,
    click_cmd,
    type_cmd,
    press,
    hotkey,
    scroll,
    drag,
    move,
)


class TestMethodFlagDefinition:
    """Verify --method flag is correctly defined."""

    def test_valid_methods_contains_auto(self):
        """'auto' must be a valid method (the default)."""
        assert "auto" in VALID_METHODS

    def test_valid_methods_contains_all_channels(self):
        """All interaction channels must be represented."""
        expected = {"auto", "cdp", "uia", "msaa", "ia2", "jab", "vision"}
        assert set(VALID_METHODS) == expected

    def test_validate_method_accepts_valid(self):
        """_validate_method returns True for valid methods."""
        for method in VALID_METHODS:
            assert _validate_method(method, json_output=False) is True


class TestMethodFlagOnCommands:
    """Verify --method is accepted by all action commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_backend(self):
        """Mock the backend to avoid needing a real desktop session."""
        backend = MagicMock()
        backend.click.return_value = None
        backend.type_text.return_value = None
        backend.press_key.return_value = None
        backend.hotkey.return_value = None
        backend.scroll.return_value = None
        backend.drag.return_value = None
        backend.move_mouse.return_value = None
        backend.clipboard_get.return_value = ""
        backend.clipboard_set.return_value = None
        return backend

    def test_click_accepts_method_flag(self, runner, mock_backend):
        """click command accepts --method."""
        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend):
            result = runner.invoke(click_cmd, ["--coords", "100", "200", "--method", "uia", "--no-verify"])
            assert result.exit_code == 0, result.output

    def test_click_accepts_method_short_flag(self, runner, mock_backend):
        """click command accepts -m shorthand."""
        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend):
            result = runner.invoke(click_cmd, ["--coords", "100", "200", "-m", "uia", "--no-verify"])
            assert result.exit_code == 0, result.output

    def test_click_rejects_invalid_method(self, runner, mock_backend):
        """click command rejects invalid --method values."""
        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend):
            result = runner.invoke(click_cmd, ["--coords", "100", "200", "--method", "invalid"])
            assert result.exit_code != 0
            assert "Invalid value" in result.output or "invalid" in result.output.lower()

    def test_type_accepts_method_flag(self, runner, mock_backend):
        """type command accepts --method."""
        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend):
            result = runner.invoke(type_cmd, ["Hello", "--method", "cdp", "--no-verify"])
            assert result.exit_code == 0, result.output

    def test_press_accepts_method_flag(self, runner, mock_backend):
        """press command accepts --method."""
        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend):
            result = runner.invoke(press, ["enter", "--method", "msaa", "--no-verify"])
            assert result.exit_code == 0, result.output

    def test_hotkey_accepts_method_flag(self, runner, mock_backend):
        """hotkey command accepts --method."""
        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend):
            result = runner.invoke(hotkey, ["ctrl+c", "--method", "ia2"])
            assert result.exit_code == 0, result.output

    def test_scroll_accepts_method_flag(self, runner, mock_backend):
        """scroll command accepts --method."""
        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend):
            result = runner.invoke(scroll, ["down", "--method", "jab"])
            assert result.exit_code == 0, result.output

    def test_drag_accepts_method_flag(self, runner, mock_backend):
        """drag command accepts --method."""
        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend):
            result = runner.invoke(drag, [
                "--from-coords", "100", "100",
                "--to-coords", "200", "200",
                "--method", "vision",
            ])
            assert result.exit_code == 0, result.output

    def test_move_accepts_method_flag(self, runner, mock_backend):
        """move command accepts --method."""
        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend):
            result = runner.invoke(move, ["--coords", "300", "400", "--method", "auto"])
            assert result.exit_code == 0, result.output


class TestMethodFlagDefaultAuto:
    """Verify --method defaults to 'auto' when omitted."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_backend(self):
        backend = MagicMock()
        backend.click.return_value = None
        return backend

    def test_click_default_method_is_auto(self, runner, mock_backend):
        """When --method is omitted, it defaults to 'auto'."""
        captured_method = {}

        original_click = click_cmd.callback

        def patched_click(*args, **kwargs):
            captured_method["value"] = kwargs.get("method", "NOT_SET")
            return original_click(*args, **kwargs)

        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend):
            with patch.object(click_cmd, "callback", patched_click):
                result = runner.invoke(click_cmd, ["--coords", "100", "200"])

        assert captured_method.get("value") == "auto"


class TestMethodFlagAllValues:
    """Verify every valid method value is accepted by action commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_backend(self):
        backend = MagicMock()
        backend.click.return_value = None
        return backend

    @pytest.mark.parametrize("method", VALID_METHODS)
    def test_click_accepts_all_valid_methods(self, runner, mock_backend, method):
        """click command accepts every valid method value."""
        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend):
            result = runner.invoke(click_cmd, ["--coords", "50", "50", "--method", method, "--no-verify"])
            assert result.exit_code == 0, f"Failed for method={method}: {result.output}"


class TestMethodFlagHelp:
    """Verify --method appears in help text for all commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.mark.parametrize("cmd", [click_cmd, type_cmd, press, hotkey, scroll, drag, move])
    def test_method_in_help(self, runner, cmd):
        """--method flag is documented in command help."""
        result = runner.invoke(cmd, ["--help"])
        assert "--method" in result.output or "-m" in result.output
