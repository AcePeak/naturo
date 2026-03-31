"""Tests for naturo.cli.core._highlight — highlight command.

Tests cover UIA/win32 backends, ref filtering, annotate mode, JSON output,
window resolution errors, and error paths. All mock-based, CI-safe.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.core._highlight import highlight


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend._resolve_hwnd.return_value = 12345
    backend.get_element_tree.return_value = MagicMock()
    return backend


def _patch_backend(mock_backend):
    return patch("naturo.cli.core._common._get_backend", return_value=mock_backend)


# ── UIA highlight (default) ─────────────────────────────────────────


class TestUiaHighlight:

    @patch("naturo.bridge.highlight_elements_uia")
    def test_basic_highlight_json(self, mock_hl, runner, mock_backend):
        with _patch_backend(mock_backend):
            result = runner.invoke(highlight, [
                "--app", "notepad", "--json", "--duration", "0.1",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["backend"] == "uia"
        assert data["hwnd"] == 12345
        mock_hl.assert_called_once()

    @patch("naturo.bridge.highlight_elements_uia")
    def test_highlight_with_refs(self, mock_hl, runner, mock_backend):
        with _patch_backend(mock_backend):
            result = runner.invoke(highlight, [
                "e5", "e10", "--app", "notepad", "--json", "--duration", "0.1",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["refs"] == ["e5", "e10"]

    @patch("naturo.bridge.highlight_elements_uia")
    def test_highlight_on_ref(self, mock_hl, runner, mock_backend):
        with _patch_backend(mock_backend):
            result = runner.invoke(highlight, [
                "--on", "e42", "--app", "notepad", "--json", "--duration", "0.1",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "e42" in data["refs"]

    @patch("naturo.bridge.highlight_elements_uia")
    def test_highlight_ref_option(self, mock_hl, runner, mock_backend):
        with _patch_backend(mock_backend):
            result = runner.invoke(highlight, [
                "-r", "e5", "-r", "e10", "--app", "notepad", "--json", "--duration", "0.1",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "e5" in data["refs"]
        assert "e10" in data["refs"]

    @patch("naturo.bridge.highlight_elements_uia")
    def test_highlight_all_flag(self, mock_hl, runner, mock_backend):
        with _patch_backend(mock_backend):
            result = runner.invoke(highlight, [
                "--app", "notepad", "--all", "--json", "--duration", "0.1",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["show_all"] is True


# ── Win32 highlight ──────────────────────────────────────────────────


class TestWin32Highlight:

    @patch("naturo.bridge.highlight_elements")
    def test_win32_backend(self, mock_hl, runner, mock_backend):
        with _patch_backend(mock_backend):
            result = runner.invoke(highlight, [
                "--app", "notepad", "--backend", "win32", "--json", "--duration", "0.1",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["backend"] == "win32"
        mock_hl.assert_called_once()


# ── Annotate mode ────────────────────────────────────────────────────


class TestAnnotateMode:

    @patch("naturo.bridge.highlight_elements_uia")
    def test_annotate_saves_file(self, mock_hl, runner, mock_backend):
        mock_hl.return_value = "/tmp/annotated.png"
        with _patch_backend(mock_backend):
            result = runner.invoke(highlight, [
                "--app", "notepad", "-A", "/tmp/annotated.png", "--json",
            ], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["annotate_path"] == "/tmp/annotated.png"

    @patch("naturo.bridge.highlight_elements_uia")
    def test_annotate_no_snapshot(self, mock_hl, runner, mock_backend):
        mock_hl.return_value = None
        with _patch_backend(mock_backend):
            result = runner.invoke(highlight, [
                "--app", "notepad", "-A", "/tmp/out.png", "--json",
            ], catch_exceptions=False)
        assert result.exit_code != 0
        assert "NO_SNAPSHOT" in result.output


# ── Window resolution errors ────────────────────────────────────────


class TestWindowResolution:

    def test_window_not_found_json(self, runner, mock_backend):
        mock_backend._resolve_hwnd.side_effect = Exception("window not found")
        with _patch_backend(mock_backend):
            result = runner.invoke(highlight, ["--app", "nonexistent", "--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "WINDOW_NOT_FOUND" in result.output


# ── Highlight error ──────────────────────────────────────────────────


class TestHighlightError:

    @patch("naturo.bridge.highlight_elements_uia")
    def test_highlight_exception_json(self, mock_hl, runner, mock_backend):
        mock_hl.side_effect = Exception("GDI error")
        with _patch_backend(mock_backend):
            result = runner.invoke(highlight, [
                "--app", "notepad", "--json", "--duration", "0.1",
            ], catch_exceptions=False)
        assert result.exit_code != 0
        assert "HIGHLIGHT_ERROR" in result.output
