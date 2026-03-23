"""Tests for type --paste without TEXT and --on element targeting (#165).

These tests verify:
1. ``type --paste`` without TEXT pastes current clipboard (Ctrl+V only)
2. ``type --paste`` with TEXT sets clipboard then Ctrl+V (existing behavior)
3. ``type "text" --on eN`` clicks element then types
4. ``type --on eN --paste`` clicks element then pastes clipboard
5. ``type`` without TEXT or --paste gives an error
"""
from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

_win_only = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Interaction commands require Windows",
)


@pytest.fixture
def runner():
    return CliRunner()


class TestTypePasteWithoutText:
    """type --paste without TEXT should paste current clipboard."""

    def test_type_no_text_no_paste_errors(self, runner):
        """type without TEXT and without --paste should give INVALID_INPUT."""
        from naturo.cli.interaction import type_cmd

        with patch("naturo.cli.interaction._get_backend"):
            result = runner.invoke(type_cmd, ["--json"])
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "INVALID_INPUT"

    @_win_only
    def test_type_paste_without_text_calls_ctrl_v(self, runner):
        """type --paste without TEXT should just press Ctrl+V."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._auto_route", return_value={}):
            result = runner.invoke(type_cmd, ["--paste", "--json"])

        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["action"] == "pasted"
        assert data["data"]["text"] == "(clipboard)"
        # Should NOT call clipboard_set — just Ctrl+V
        mock_backend.clipboard_set.assert_not_called()
        mock_backend.hotkey.assert_called_once_with("ctrl", "v")

    @_win_only
    def test_type_paste_with_text_sets_clipboard(self, runner):
        """type "hello" --paste should set clipboard then Ctrl+V."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()
        mock_backend.clipboard_get.return_value = ""

        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._auto_route", return_value={}):
            result = runner.invoke(type_cmd, ["hello", "--paste", "--json"])

        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["action"] == "pasted"
        assert data["data"]["text"] == "hello"
        mock_backend.clipboard_set.assert_called()
        mock_backend.hotkey.assert_called_with("ctrl", "v")


class TestTypeOnElement:
    """type --on should click target element before typing."""

    def test_type_has_on_param(self):
        """type command should accept --on option."""
        from naturo.cli.interaction import type_cmd

        param_names = [p.name for p in type_cmd.params]
        assert "on_element" in param_names

    @_win_only
    def test_type_on_eref_clicks_then_types(self, runner):
        """type "hello" --on e5 should resolve ref, click, then type."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._auto_route", return_value={}), \
             patch("naturo.snapshot.SnapshotManager") as MockMgr:
            mock_mgr = MockMgr.return_value
            mock_mgr.resolve_ref.return_value = (100, 200)

            result = runner.invoke(type_cmd, ["hello", "--on", "e5", "--json"])

        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["target"] == "e5"
        # Should click the element coordinates first
        mock_backend.click.assert_called_once_with(100, 200, button="left", input_mode="normal")
        # Then type
        mock_backend.type_text.assert_called_once()

    @_win_only
    def test_type_on_eref_not_found(self, runner):
        """type --on e99 with missing ref should error."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._auto_route", return_value={}), \
             patch("naturo.snapshot.SnapshotManager") as MockMgr:
            mock_mgr = MockMgr.return_value
            mock_mgr.resolve_ref.return_value = None

            result = runner.invoke(type_cmd, ["hello", "--on", "e99", "--json"])

        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] == "REF_NOT_FOUND"

    @_win_only
    def test_type_on_with_paste_clicks_then_pastes(self, runner):
        """type --paste --on e5 should click then paste clipboard."""
        from naturo.cli.interaction import type_cmd

        mock_backend = MagicMock()

        with patch("naturo.cli.interaction._get_backend", return_value=mock_backend), \
             patch("naturo.cli.interaction._auto_route", return_value={}), \
             patch("naturo.snapshot.SnapshotManager") as MockMgr:
            mock_mgr = MockMgr.return_value
            mock_mgr.resolve_ref.return_value = (100, 200)

            result = runner.invoke(type_cmd, ["--paste", "--on", "e5", "--json"])

        data = json.loads(result.output)
        assert data["success"] is True
        assert data["data"]["action"] == "pasted"
        assert data["data"]["target"] == "e5"
        # Should click, then Ctrl+V (no clipboard_set since no text)
        mock_backend.click.assert_called_once()
        mock_backend.hotkey.assert_called_once_with("ctrl", "v")
        mock_backend.clipboard_set.assert_not_called()
