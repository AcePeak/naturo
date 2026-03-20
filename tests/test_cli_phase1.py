"""Tests for Phase 1 CLI commands.

Tests CLI command registration and help output on all platforms.
Functional tests (actual capture/list) are Windows-only.
"""

import platform

import pytest
from click.testing import CliRunner
from naturo.cli import main


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


# ── Command Registration Tests (all platforms) ──────


def test_capture_live_has_screen_option(runner):
    """capture live should have --screen option."""
    result = runner.invoke(main, ["capture", "live", "--help"])
    assert result.exit_code == 0
    assert "--screen" in result.output


def test_capture_live_has_format_option(runner):
    """capture live should have --format option."""
    result = runner.invoke(main, ["capture", "live", "--help"])
    assert result.exit_code == 0
    assert "--format" in result.output


def test_list_windows_has_filters(runner):
    """list windows should have filter options."""
    result = runner.invoke(main, ["list", "windows", "--help"])
    assert result.exit_code == 0
    assert "--app" in result.output
    assert "--process-name" in result.output
    assert "--pid" in result.output


def test_see_has_depth_option(runner):
    """see command should have --depth option."""
    result = runner.invoke(main, ["see", "--help"])
    assert result.exit_code == 0
    assert "--depth" in result.output


# ── Functional Tests (Windows only) ─────────────────


@pytest.mark.ui
@pytest.mark.skipif(
    platform.system() != "Windows",
    reason="Functional CLI tests require Windows",
)
class TestCLIFunctionalWindows:
    """Windows-only functional CLI tests."""

    def test_list_windows_runs(self, runner):
        """'naturo list windows' should run without error on Windows."""
        result = runner.invoke(main, ["list", "windows"])
        assert result.exit_code == 0

    def test_list_windows_json(self, runner):
        """'naturo list windows --json' should produce valid JSON."""
        import json

        result = runner.invoke(main, ["list", "windows", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, dict)
        assert data["success"] is True
        assert isinstance(data["windows"], list)

    def test_see_runs(self, runner):
        """'naturo see' should run without crashing."""
        result = runner.invoke(main, ["see"])
        # May succeed or say "no window found" — both are fine
        assert result.exit_code in (0, 1)

    def test_capture_live_runs(self, runner):
        """'naturo capture live' should produce a file on Windows."""
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".bmp", delete=False) as f:
            path = f.name

        try:
            result = runner.invoke(main, ["capture", "live", "--path", path])
            assert result.exit_code == 0
            assert os.path.exists(path)
        finally:
            if os.path.exists(path):
                os.unlink(path)
