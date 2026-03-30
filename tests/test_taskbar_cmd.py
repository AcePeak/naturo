"""Tests for naturo.cli.taskbar_cmd — taskbar list and click commands."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.taskbar_cmd import taskbar


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    return backend


class TestTaskbarList:
    """Tests for 'naturo taskbar list' command."""

    def test_list_empty(self, runner, mock_backend):
        mock_backend.taskbar_list.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(taskbar, ["list"])
        assert result.exit_code == 0
        assert "No taskbar items found." in result.output

    def test_list_with_items(self, runner, mock_backend):
        mock_backend.taskbar_list.return_value = [
            {"name": "Notepad", "is_active": True, "is_pinned": False},
            {"name": "Chrome", "is_active": False, "is_pinned": True},
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(taskbar, ["list"])
        assert result.exit_code == 0
        assert "Notepad" in result.output
        assert "[active]" in result.output
        assert "Chrome" in result.output
        assert "[pinned]" in result.output

    def test_list_json_output(self, runner, mock_backend):
        items = [{"name": "Notepad", "is_active": True, "is_pinned": False}]
        mock_backend.taskbar_list.return_value = items
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(taskbar, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 1
        assert data["items"][0]["name"] == "Notepad"

    def test_list_json_empty(self, runner, mock_backend):
        mock_backend.taskbar_list.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(taskbar, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 0

    def test_list_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.taskbar_list.side_effect = NaturoError("BACKEND_ERROR", "Not supported")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(taskbar, ["list"])
        # Error should be emitted, not crash
        assert result.exit_code != 0 or "error" in result.output.lower() or "Error" in result.output

    def test_list_unexpected_error(self, runner, mock_backend):
        mock_backend.taskbar_list.side_effect = RuntimeError("unexpected")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(taskbar, ["list"])
        assert result.exit_code != 0 or "error" in result.output.lower() or "Error" in result.output


class TestTaskbarClick:
    """Tests for 'naturo taskbar click' command."""

    def test_click_success(self, runner, mock_backend):
        mock_backend.taskbar_click.return_value = {"name": "Notepad"}
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(taskbar, ["click", "Notepad"])
        assert result.exit_code == 0
        assert "Clicked taskbar item 'Notepad'" in result.output
        mock_backend.taskbar_click.assert_called_once_with(name="Notepad")

    def test_click_json_output(self, runner, mock_backend):
        mock_backend.taskbar_click.return_value = {"name": "Chrome"}
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(taskbar, ["click", "Chrome", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["name"] == "Chrome"

    def test_click_missing_name_argument(self, runner):
        result = runner.invoke(taskbar, ["click"])
        assert result.exit_code != 0

    def test_click_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.taskbar_click.side_effect = NaturoError("ELEMENT_NOT_FOUND", "Not found")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(taskbar, ["click", "Nonexistent"])
        assert result.exit_code != 0 or "error" in result.output.lower() or "Error" in result.output

    def test_click_empty_name(self, runner, mock_backend):
        """Empty name triggers INVALID_INPUT error."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(taskbar, ["click", "   "])
        assert result.exit_code != 0 or "INVALID_INPUT" in result.output
        mock_backend.taskbar_click.assert_not_called()

    def test_click_empty_name_json(self, runner, mock_backend):
        """Empty name with JSON output emits structured error."""
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(taskbar, ["click", "  ", "--json"])
        assert result.exit_code != 0 or "INVALID_INPUT" in result.output
        mock_backend.taskbar_click.assert_not_called()

    def test_click_generic_exception(self, runner, mock_backend):
        """Generic exception from backend is emitted with UNKNOWN_ERROR."""
        mock_backend.taskbar_click.side_effect = RuntimeError("unexpected crash")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(taskbar, ["click", "Chrome"])
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_click_naturo_error_json(self, runner, mock_backend):
        """NaturoError in JSON mode returns structured error."""
        from naturo.errors import NaturoError
        mock_backend.taskbar_click.side_effect = NaturoError("ELEMENT_NOT_FOUND", "Item not found")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(taskbar, ["click", "Missing", "--json"])
        data = json.loads(result.output)
        assert data.get("success") is False or "ELEMENT_NOT_FOUND" in result.output


class TestTaskbarHelp:
    """Tests for taskbar command help text."""

    def test_taskbar_help(self, runner):
        result = runner.invoke(taskbar, ["--help"])
        assert result.exit_code == 0
        assert "taskbar" in result.output.lower()

    def test_taskbar_list_help(self, runner):
        result = runner.invoke(taskbar, ["list", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_taskbar_click_help(self, runner):
        result = runner.invoke(taskbar, ["click", "--help"])
        assert result.exit_code == 0
        assert "NAME" in result.output
