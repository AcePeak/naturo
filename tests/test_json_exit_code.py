"""Tests for JSON exit code consistency (#781).

Verifies that when CLI commands output {"success": false, ...} as JSON,
the process exits with a non-zero exit code.  AI agents rely on both
the JSON payload AND the exit code to detect failures — they must agree.
"""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    return CliRunner()


# ── selector clear: no selectors ────────────────────────────────────────────

def test_selector_clear_empty_json_exit_code(runner):
    """selector clear with no selectors should exit non-zero in JSON mode."""
    from naturo.cli.selector_cmd import selector_clear

    with patch("naturo.cli.selector_cmd._load_selectors", return_value={}):
        result = runner.invoke(selector_clear, ["nonexistent_app", "--json"])

    assert result.exit_code != 0, (
        f"Expected non-zero exit code when no selectors found, got {result.exit_code}"
    )
    data = json.loads(result.output.strip())
    assert data["success"] is False


def test_selector_clear_empty_text_exit_code(runner):
    """selector clear with no selectors should exit non-zero in text mode."""
    from naturo.cli.selector_cmd import selector_clear

    with patch("naturo.cli.selector_cmd._load_selectors", return_value={}):
        result = runner.invoke(selector_clear, ["nonexistent_app"])

    assert result.exit_code != 0


# ── selector export: no selectors ───────────────────────────────────���───────

def test_selector_export_empty_json_exit_code(runner):
    """selector export with no selectors should exit non-zero in JSON mode."""
    from naturo.cli.selector_cmd import selector_export

    with patch("naturo.cli.selector_cmd._load_selectors", return_value={}), \
         patch("naturo.cli.selector_cmd._list_builtin_selectors", return_value={}):
        result = runner.invoke(selector_export, ["nonexistent_app", "--json"])

    assert result.exit_code != 0, (
        f"Expected non-zero exit code when no selectors found, got {result.exit_code}"
    )
    data = json.loads(result.output.strip())
    assert data["success"] is False


def test_selector_export_empty_text_exit_code(runner):
    """selector export with no selectors should exit non-zero in text mode."""
    from naturo.cli.selector_cmd import selector_export

    with patch("naturo.cli.selector_cmd._load_selectors", return_value={}), \
         patch("naturo.cli.selector_cmd._list_builtin_selectors", return_value={}):
        result = runner.invoke(selector_export, ["nonexistent_app"])

    assert result.exit_code != 0


# ── visual report: no baselines ────────────���────────────────────────────────

def test_visual_report_no_baselines_json_exit_code(runner, tmp_path):
    """visual report with no baselines should exit non-zero in JSON mode."""
    from naturo.cli.visual_cmd import visual_report

    with patch("naturo.cli.visual_cmd.list_baselines", return_value=[]):
        result = runner.invoke(visual_report, ["--current-dir", str(tmp_path), "--json"])

    assert result.exit_code != 0, (
        f"Expected non-zero exit code when no baselines, got {result.exit_code}"
    )
    data = json.loads(result.output.strip())
    assert data["success"] is False


def test_visual_report_no_baselines_text_exit_code(runner, tmp_path):
    """visual report with no baselines should exit non-zero in text mode."""
    from naturo.cli.visual_cmd import visual_report

    with patch("naturo.cli.visual_cmd.list_baselines", return_value=[]):
        result = runner.invoke(visual_report, ["--current-dir", str(tmp_path)])

    assert result.exit_code != 0
