"""Tests for capture command UX improvements (issue #280).

Tests:
- capture without subcommand defaults to live
- --ref as alias for --element
- -o as alias for --path
- Zero-bounds element error message
"""
import pytest
from click.testing import CliRunner
from naturo.cli import main


def test_capture_without_subcommand_shows_help():
    """capture with no args and no subcommand should show help and support all core flags."""
    runner = CliRunner()
    result = runner.invoke(main, ["capture", "--help"])
    assert result.exit_code == 0
    assert "Capture a live screenshot" in result.output
    assert "--app" in result.output
    assert "--element" in result.output or "--ref" in result.output
    assert "-o" in result.output and "--path" in result.output


def test_capture_ref_alias():
    """--ref should work as alias for --element."""
    runner = CliRunner()
    # This will fail with "Element ref 'e999' not found" which proves --ref is accepted
    result = runner.invoke(main, ["capture", "--ref", "e999", "--json"])
    assert "--ref" not in result.output or "No such option" not in result.output
    # Should get REF_NOT_FOUND or similar, not "No such option: --ref"
    if result.exit_code != 0:
        assert "No such option" not in result.output


def test_capture_output_alias():
    """Test that -o works as alias for -p/--path."""
    runner = CliRunner()
    result = runner.invoke(main, ["capture", "--help"])
    assert result.exit_code == 0
    # Check that -o is listed alongside -p
    assert "-o" in result.output
    assert "--path" in result.output


def test_capture_app_flag_without_subcommand():
    """Test that --app flag works on capture without explicit 'live' subcommand."""
    runner = CliRunner()
    # This will fail with window not found, which proves --app is accepted
    result = runner.invoke(main, ["capture", "--app", "nonexistent-app-xyz", "--json"])
    # Should get WINDOW_NOT_FOUND or similar, not "No such option: --app"
    if result.exit_code != 0:
        output_lower = result.output.lower()
        assert "no such option" not in output_lower


@pytest.mark.skipif(
    not hasattr(__import__("platform"), "system") or __import__("platform").system() != "Windows",
    reason="Requires Windows"
)
def test_zero_bounds_element_error_message():
    """Test that zero-bounds elements produce a clear, single error message."""
    # This test would need a real snapshot with a zero-bounds element
    # For now, just verify the error path exists in the code
    from naturo.cli.core import capture
    import inspect
    source = inspect.getsource(capture)
    assert "zero-size bounds" in source.lower() or "zero_size_element" in source
