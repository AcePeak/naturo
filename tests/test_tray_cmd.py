"""Tests for naturo.cli.tray_cmd — system tray list and click commands."""

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.tray_cmd import tray


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    return backend


class TestTrayList:
    """Tests for 'naturo tray list' command."""

    def test_list_empty(self, runner, mock_backend):
        mock_backend.tray_list.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(tray, ["list"])
        assert result.exit_code == 0
        assert "No tray icons found." in result.output

    def test_list_with_icons(self, runner, mock_backend):
        mock_backend.tray_list.return_value = [
            {"name": "Volume", "tooltip": "Speakers: 50%", "is_visible": True},
            {"name": "Wi-Fi", "tooltip": "Wi-Fi", "is_visible": True},
            {"name": "Dropbox", "tooltip": "Up to date", "is_visible": False},
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(tray, ["list"])
        assert result.exit_code == 0
        assert "Volume" in result.output
        assert "Speakers: 50%" in result.output
        assert "Dropbox" in result.output
        assert "[hidden]" in result.output

    def test_list_tooltip_same_as_name_not_duplicated(self, runner, mock_backend):
        """When tooltip equals name, it should not be shown again."""
        mock_backend.tray_list.return_value = [
            {"name": "Wi-Fi", "tooltip": "Wi-Fi", "is_visible": True},
        ]
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(tray, ["list"])
        assert result.exit_code == 0
        # "Wi-Fi" appears once (the name), not " — Wi-Fi" tooltip
        assert result.output.count("Wi-Fi") == 1

    def test_list_json_output(self, runner, mock_backend):
        icons = [{"name": "Volume", "tooltip": "50%", "is_visible": True}]
        mock_backend.tray_list.return_value = icons
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(tray, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 1
        assert data["icons"][0]["name"] == "Volume"

    def test_list_json_empty(self, runner, mock_backend):
        mock_backend.tray_list.return_value = []
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(tray, ["list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == 0

    def test_list_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.tray_list.side_effect = NaturoError("BACKEND_ERROR", "Not supported")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(tray, ["list"])
        assert result.exit_code != 0 or "error" in result.output.lower() or "Error" in result.output


class TestTrayClick:
    """Tests for 'naturo tray click' command."""

    def test_click_left(self, runner, mock_backend):
        mock_backend.tray_click.return_value = {"name": "Volume"}
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(tray, ["click", "Volume"])
        assert result.exit_code == 0
        assert "Clicked tray icon 'Volume'" in result.output
        mock_backend.tray_click.assert_called_once_with(name="Volume", button="left", double=False)

    def test_click_right(self, runner, mock_backend):
        mock_backend.tray_click.return_value = {"name": "Wi-Fi"}
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(tray, ["click", "Wi-Fi", "--right"])
        assert result.exit_code == 0
        assert "Right-clicked tray icon 'Wi-Fi'" in result.output
        mock_backend.tray_click.assert_called_once_with(name="Wi-Fi", button="right", double=False)

    def test_click_double(self, runner, mock_backend):
        mock_backend.tray_click.return_value = {"name": "Dropbox"}
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(tray, ["click", "Dropbox", "--double"])
        assert result.exit_code == 0
        assert "Double-clicked tray icon 'Dropbox'" in result.output
        mock_backend.tray_click.assert_called_once_with(name="Dropbox", button="left", double=True)

    def test_click_json_output(self, runner, mock_backend):
        mock_backend.tray_click.return_value = {"name": "Volume"}
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(tray, ["click", "Volume", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["name"] == "Volume"

    def test_click_missing_name(self, runner):
        result = runner.invoke(tray, ["click"])
        assert result.exit_code != 0

    def test_click_naturo_error(self, runner, mock_backend):
        from naturo.errors import NaturoError
        mock_backend.tray_click.side_effect = NaturoError("ELEMENT_NOT_FOUND", "Icon not found")
        with patch("naturo.backends.base.get_backend", return_value=mock_backend):
            result = runner.invoke(tray, ["click", "Nonexistent"])
        assert result.exit_code != 0 or "error" in result.output.lower() or "Error" in result.output


class TestTrayHelp:
    """Tests for tray command help text."""

    def test_tray_help(self, runner):
        result = runner.invoke(tray, ["--help"])
        assert result.exit_code == 0
        assert "tray" in result.output.lower()

    def test_tray_list_help(self, runner):
        result = runner.invoke(tray, ["list", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_tray_click_help(self, runner):
        result = runner.invoke(tray, ["click", "--help"])
        assert result.exit_code == 0
        assert "--right" in result.output
        assert "--double" in result.output
        assert "NAME" in result.output
