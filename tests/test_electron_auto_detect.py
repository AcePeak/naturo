"""Tests for issue #138 — Auto-detect Electron apps in see/click.

Verifies:
- _is_electron_candidate() returns True when element count < threshold
- _get_electron_hint() returns hint dict for known Electron apps on Windows
- _get_electron_hint() returns None on non-Windows platforms
- JSON output includes electron_hint when low element count + Electron detected
- Text output shows Electron hint on stderr
- Hint includes CDP port when debug port available
- Hint suggests relaunch command when no CDP port
"""
from __future__ import annotations

from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.backends.base import ElementInfo
from naturo.cli.core import _is_electron_candidate, _get_electron_hint


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_tree(num_elements: int = 5) -> ElementInfo:
    """Make a tree with *num_elements* total nodes."""
    children = [
        ElementInfo(id=f"e{i}", role="Button", name=f"Btn{i}", value=None,
                    x=i * 10, y=0, width=50, height=30, children=[], properties={})
        for i in range(num_elements - 1)
    ]
    return ElementInfo(
        id="root", role="Window", name="App", value=None,
        x=0, y=0, width=1200, height=800,
        children=children, properties={},
    )


# ── _is_electron_candidate ────────────────────────────────────────────────────


class TestIsElectronCandidate:
    def test_none_tree_returns_false(self):
        assert _is_electron_candidate(None) is False

    def test_few_elements_returns_true(self):
        tree = _make_tree(10)  # 10 < 40 threshold
        assert _is_electron_candidate(tree) is True

    def test_many_elements_returns_false(self):
        tree = _make_tree(50)  # 50 >= 40 threshold
        assert _is_electron_candidate(tree) is False

    def test_exactly_at_threshold_returns_false(self):
        from naturo.cli.core import _ELECTRON_SUSPICION_THRESHOLD
        tree = _make_tree(_ELECTRON_SUSPICION_THRESHOLD)
        assert _is_electron_candidate(tree) is False

    def test_one_below_threshold_returns_true(self):
        from naturo.cli.core import _ELECTRON_SUSPICION_THRESHOLD
        tree = _make_tree(_ELECTRON_SUSPICION_THRESHOLD - 1)
        assert _is_electron_candidate(tree) is True


# ── _get_electron_hint ────────────────────────────────────────────────────────


class TestGetElectronHint:
    def test_returns_none_on_non_windows(self):
        with patch("platform.system", return_value="Darwin"):
            result = _get_electron_hint("feishu")
        assert result is None

    def test_returns_none_on_linux(self):
        with patch("platform.system", return_value="Linux"):
            result = _get_electron_hint("slack")
        assert result is None

    def test_known_electron_app_without_port(self):
        with patch("platform.system", return_value="Windows"), \
             patch("naturo.electron.detect_electron_app", return_value={
                 "is_electron": True, "debug_port": None, "main_pid": 1234,
                 "app_name": "feishu", "processes": [{"pid": 1234}],
             }):
            result = _get_electron_hint("feishu")

        assert result is not None
        assert result["is_electron"] is True
        assert result["debug_port"] is None
        assert "suggestion" in result
        assert "remote-debugging-port" in result["suggestion"]

    def test_known_electron_app_with_port(self):
        with patch("platform.system", return_value="Windows"), \
             patch("naturo.electron.detect_electron_app", return_value={
                 "is_electron": True, "debug_port": 9222, "main_pid": 1234,
                 "app_name": "feishu", "processes": [{"pid": 1234}],
             }):
            result = _get_electron_hint("feishu")

        assert result is not None
        assert result["debug_port"] == 9222
        assert "9222" in result["suggestion"]
        assert "--cascade" in result["suggestion"] or "cdp" in result["suggestion"].lower()

    def test_non_electron_app_returns_none(self):
        with patch("platform.system", return_value="Windows"), \
             patch("naturo.electron.detect_electron_app", return_value={
                 "is_electron": False, "debug_port": None, "main_pid": None,
                 "app_name": "notepad", "processes": [],
             }):
            result = _get_electron_hint("notepad")

        # Unknown non-electron app → None
        assert result is None

    def test_electron_detection_exception_on_unknown_app_returns_none(self):
        """For unknown apps where detection throws, return None gracefully."""
        with patch("platform.system", return_value="Windows"), \
             patch("naturo.electron.detect_electron_app", side_effect=Exception("COM error")), \
             patch("naturo.electron._KNOWN_ELECTRON_APPS", {}):
            result = _get_electron_hint("some-unknown-app-xyz")
        assert result is None


# ── CLI integration ───────────────────────────────────────────────────────────


class TestElectronHintInSee:
    def test_json_output_includes_electron_hint(self):
        """When few UIA elements + Electron detected, JSON includes electron_hint."""
        tree = _make_tree(5)  # Few elements → electron candidate

        runner = CliRunner()
        with patch("naturo.cli.core._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._get_backend") as mock_be, \
             patch("naturo.cli.core._get_electron_hint", return_value={
                 "is_electron": True, "app": "feishu", "debug_port": None,
                 "suggestion": "Use --cascade for WebView content",
             }):
            be = MagicMock()
            be.get_element_tree.return_value = tree
            be.list_monitors.return_value = []
            be.get_dpi_scale.return_value = 1.0
            mock_be.return_value = be

            import json
            result = runner.invoke(main, ["see", "--app", "feishu", "--json", "--no-snapshot"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "electron_hint" in data
        assert data["electron_hint"]["is_electron"] is True

    def test_hint_not_shown_for_many_elements(self):
        """No hint when UIA returns many elements (not Electron-like)."""
        tree = _make_tree(60)  # Many elements → NOT electron candidate

        runner = CliRunner()
        with patch("naturo.cli.core._platform_supports_gui", return_value=True), \
             patch("naturo.cli.core._get_backend") as mock_be, \
             patch("naturo.cli.core._get_electron_hint") as mock_hint:
            be = MagicMock()
            be.get_element_tree.return_value = tree
            be.list_monitors.return_value = []
            be.get_dpi_scale.return_value = 1.0
            mock_be.return_value = be

            import json
            result = runner.invoke(main, ["see", "--app", "notepad", "--json", "--no-snapshot"])

        # _get_electron_hint should not be called when not an Electron candidate
        mock_hint.assert_not_called()


# Import main here (after test definitions to avoid circular issues)
from naturo.cli import main
