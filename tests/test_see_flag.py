"""Tests for the --see flag on interaction commands (click, type, press, hotkey, scroll).

The --see flag re-captures the UI element tree after an interaction completes,
enabling AI agents to observe the effect of their actions without a separate
``see`` call.
"""
from __future__ import annotations

import json
import sys
import types
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

# Most tests require Windows backend, but decorator/parameter tests can run anywhere
_win_only = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Interaction commands require Windows",
)


@pytest.fixture
def runner():
    return CliRunner(mix_stderr=False)


def _make_mock_tree():
    """Build a minimal mock element tree for _post_action_see."""
    root = MagicMock()
    root.id = 1
    root.role = "Window"
    root.name = "Test App"
    root.value = ""
    root.x, root.y, root.width, root.height = 0, 0, 800, 600
    root.children = []
    root.properties = {}
    root.is_actionable = False

    child = MagicMock()
    child.id = 2
    child.role = "Button"
    child.name = "OK"
    child.value = ""
    child.x, child.y, child.width, child.height = 100, 200, 80, 30
    child.children = []
    child.properties = {}
    child.is_actionable = True

    root.children = [child]
    return root


def _make_backend_mock(tree=None):
    """Create a mock backend that returns a fake element tree."""
    if tree is None:
        tree = _make_mock_tree()
    backend = MagicMock()
    backend.get_element_tree.return_value = tree
    backend.get_window_handle.return_value = 12345
    backend.click_element.return_value = None
    backend.type_text.return_value = None
    backend.press_key.return_value = None
    backend.hotkey.return_value = None
    backend.scroll.return_value = None
    backend.send_keys.return_value = None
    return backend


@_win_only
class TestPostActionSeeWin:
    """Placeholder for Windows-only integration tests."""
    pass


class TestSeeOptionsDecorator:
    """Test that _see_options adds --see and --settle to commands."""

    def test_click_has_see_flag(self):
        from naturo.cli.interaction import click_cmd
        param_names = [p.name for p in click_cmd.params]
        assert "see_after" in param_names, "click should have --see flag"
        assert "settle" in param_names, "click should have --settle flag"

    def test_type_has_see_flag(self):
        from naturo.cli.interaction import type_cmd
        param_names = [p.name for p in type_cmd.params]
        assert "see_after" in param_names
        assert "settle" in param_names

    def test_press_has_see_flag(self):
        from naturo.cli.interaction import press
        param_names = [p.name for p in press.params]
        assert "see_after" in param_names
        assert "settle" in param_names

    def test_hotkey_has_see_flag(self):
        from naturo.cli.interaction import hotkey
        param_names = [p.name for p in hotkey.params]
        assert "see_after" in param_names
        assert "settle" in param_names

    def test_scroll_has_see_flag(self):
        from naturo.cli.interaction import scroll
        param_names = [p.name for p in scroll.params]
        assert "see_after" in param_names
        assert "settle" in param_names


@_win_only
class TestPostActionSee:
    """Test _post_action_see helper directly."""

    def test_returns_snapshot_json(self):
        from naturo.cli.interaction import _post_action_see
        backend = _make_backend_mock()
        result = _post_action_see(
            backend=backend,
            settle_ms=0,
            app=None,
            window_title=None,
            hwnd=None,
            json_output=True,
            depth=3,
        )
        assert result is not None
        assert "id" in result
        assert "elements" in result
        # Root element should be present
        assert result["elements"]["role"] == "Window"
        assert result["elements"]["name"] == "Test App"

    def test_returns_snapshot_text(self):
        from naturo.cli.interaction import _post_action_see
        backend = _make_backend_mock()
        result = _post_action_see(
            backend=backend,
            settle_ms=0,
            app=None,
            window_title=None,
            hwnd=None,
            json_output=False,
            depth=3,
        )
        assert result is not None
        assert "id" in result

    def test_returns_none_on_empty_tree(self):
        from naturo.cli.interaction import _post_action_see
        backend = _make_backend_mock()
        backend.get_element_tree.return_value = None
        result = _post_action_see(
            backend=backend,
            settle_ms=0,
            app=None,
            window_title=None,
            hwnd=None,
            json_output=True,
        )
        assert result is None

    def test_returns_none_on_exception(self):
        from naturo.cli.interaction import _post_action_see
        backend = _make_backend_mock()
        backend.get_element_tree.side_effect = RuntimeError("No desktop")
        result = _post_action_see(
            backend=backend,
            settle_ms=0,
            app=None,
            window_title=None,
            hwnd=None,
            json_output=True,
        )
        assert result is None

    def test_settle_delay_respected(self):
        """Verify that settle_ms causes a sleep before capture."""
        from naturo.cli.interaction import _post_action_see
        backend = _make_backend_mock()
        with patch("time.sleep") as mock_sleep:
            _post_action_see(
                backend=backend,
                settle_ms=500,
                app=None,
                window_title=None,
                hwnd=None,
                json_output=True,
            )
            mock_sleep.assert_called_once_with(0.5)

    def test_no_sleep_when_settle_zero(self):
        from naturo.cli.interaction import _post_action_see
        backend = _make_backend_mock()
        with patch("time.sleep") as mock_sleep:
            _post_action_see(
                backend=backend,
                settle_ms=0,
                app=None,
                window_title=None,
                hwnd=None,
                json_output=True,
            )
            mock_sleep.assert_not_called()

    def test_json_tree_has_children(self):
        from naturo.cli.interaction import _post_action_see
        backend = _make_backend_mock()
        result = _post_action_see(
            backend=backend,
            settle_ms=0,
            app=None,
            window_title=None,
            hwnd=None,
            json_output=True,
        )
        assert result is not None
        children = result["elements"]["children"]
        assert len(children) == 1
        assert children[0]["role"] == "Button"
        assert children[0]["name"] == "OK"


class TestSettleDefault:
    """Test that --settle defaults to 300ms."""

    def test_settle_default_value(self):
        from naturo.cli.interaction import click_cmd
        for p in click_cmd.params:
            if p.name == "settle":
                assert p.default == 300
                break
        else:
            pytest.fail("--settle param not found on click_cmd")
