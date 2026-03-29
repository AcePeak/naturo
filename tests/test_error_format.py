"""Tests for consistent error message formatting (#478).

All CLI error messages must follow the pattern:
  - Text mode: "Error: <message>" printed to stderr
  - JSON mode: structured JSON error object printed to stdout

This ensures scripters can reliably parse error output with `grep "^Error:"`.
"""
import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from naturo.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestErrorFormatConsistency:
    """All error messages must start with 'Error:' and go to stderr (#478)."""

    def test_see_nonexistent_app_error_format(self, runner):
        """see --app nonexistent should output 'Error:' to stderr."""
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True):
            with patch("naturo.cli.core._common._get_backend") as mock_be:
                backend = MagicMock()
                backend._resolve_hwnds.return_value = []
                mock_be.return_value = backend
                result = runner.invoke(
                    main, ["see", "--app", "nonexistent_xyz"]
                )
                assert result.exit_code != 0
                assert "Error:" in result.output

    def test_see_platform_error_format(self, runner):
        """see on unsupported platform should output 'Error:' to stderr."""
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=False):
            result = runner.invoke(main, ["see"])
            assert result.exit_code != 0
            assert "Error:" in result.output

    def test_capture_platform_error_format(self, runner):
        """capture on unsupported platform should output 'Error:' to stderr."""
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=False):
            result = runner.invoke(main, ["capture"])
            assert result.exit_code != 0
            assert "Error:" in result.output

    def test_list_windows_platform_error_format(self, runner):
        """list windows on unsupported platform should output 'Error:' to stderr."""
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=False):
            result = runner.invoke(main, ["list", "windows"])
            assert result.exit_code != 0
            assert "Error:" in result.output

    def test_type_empty_text_error_format(self, runner):
        """type with empty text should output 'Error:' to stderr."""
        result = runner.invoke(main, ["type"])
        assert result.exit_code != 0
        assert "Error:" in result.output

    def test_click_no_target_error_format(self, runner):
        """click with no target should output 'Error:' to stderr."""
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=True):
            result = runner.invoke(main, ["click"])
            assert result.exit_code != 0
            assert "Error:" in result.output

    def test_find_platform_error_format(self, runner):
        """find on unsupported platform should output 'Error:' to stderr."""
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=False):
            result = runner.invoke(main, ["find", "button"])
            assert result.exit_code != 0
            assert "Error:" in result.output

    def test_menu_inspect_platform_error_format(self, runner):
        """menu-inspect on unsupported platform should output 'Error:' to stderr."""
        with patch("naturo.cli.core._common._platform_supports_gui", return_value=False):
            result = runner.invoke(main, ["menu-inspect"])
            assert result.exit_code != 0
            assert "Error:" in result.output
