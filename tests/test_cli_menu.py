"""Tests for naturo.cli.core._menu — menu-inspect command.

Tests cover menu tree display, flat mode, JSON output, app not found,
no menu items, platform check, and error paths. All mock-based, CI-safe.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.core._menu import menu_inspect


def _make_menu_item(name="File", shortcut=None, enabled=True, checked=False, submenu=None):
    """Create a mock menu item."""
    item = MagicMock()
    item.name = name
    item.shortcut = shortcut
    item.enabled = enabled
    item.checked = checked
    item.submenu = submenu or []
    item.to_dict.return_value = {
        "name": name,
        "shortcut": shortcut,
        "enabled": enabled,
        "checked": checked,
        "children": [s.to_dict() for s in (submenu or [])],
    }
    item.flatten.return_value = [
        {"path": f"File > {name}" if name != "File" else name, "shortcut": shortcut},
    ]
    return item


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    sub_new = _make_menu_item(name="New", shortcut="Ctrl+N")
    sub_open = _make_menu_item(name="Open", shortcut="Ctrl+O")
    file_menu = _make_menu_item(name="File", submenu=[sub_new, sub_open])
    file_menu.flatten.return_value = [
        {"path": "File > New", "shortcut": "Ctrl+N"},
        {"path": "File > Open", "shortcut": "Ctrl+O"},
    ]
    edit_menu = _make_menu_item(name="Edit")
    edit_menu.flatten.return_value = [{"path": "Edit", "shortcut": None}]
    backend.get_menu_items.return_value = [file_menu, edit_menu]
    return backend


def _patch_backend(mock_backend):
    return patch("naturo.cli.core._common._get_backend", return_value=mock_backend)


def _patch_platform(supports=True):
    return patch("naturo.cli.core._common._platform_supports_gui", return_value=supports)


# ── Menu tree display ────────────────────────────────────────────────


class TestMenuTree:

    def test_json_output(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(menu_inspect, ["--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert len(data["menu_items"]) == 2

    def test_plain_output(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(menu_inspect, [], catch_exceptions=False)
        assert result.exit_code == 0
        assert "File" in result.output

    def test_flat_json_output(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(menu_inspect, ["--flat", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        # Flattened entries from both menus
        assert any("File > New" in str(item) for item in data["menu_items"])

    def test_flat_plain_output(self, runner, mock_backend):
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(menu_inspect, ["--flat"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "File > New" in result.output
        assert "Ctrl+N" in result.output


# ── No menu items ────────────────────────────────────────────────────


class TestNoMenuItems:

    def test_no_items_json(self, runner, mock_backend):
        mock_backend.get_menu_items.return_value = []
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(menu_inspect, ["--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "NO_MENU_ITEMS" in result.output

    def test_no_items_plain(self, runner, mock_backend):
        mock_backend.get_menu_items.return_value = []
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(menu_inspect, [], catch_exceptions=False)
        assert result.exit_code != 0


# ── App filter ───────────────────────────────────────────────────────


class TestAppFilter:

    def test_app_passed_to_backend(self, runner, mock_backend):
        # (#871) --app is resolved to a concrete handle via the shared
        # _resolve_hwnd resolver, then that handle is inspected.  This keeps
        # window targeting consistent with see/click/highlight and avoids the
        # old conflation of passing the app name as a window title.
        mock_backend._resolve_hwnd.return_value = 12345
        with _patch_platform(), _patch_backend(mock_backend), \
             patch("naturo.process.find_process", return_value={"name": "notepad"}):
            result = runner.invoke(menu_inspect, ["--app", "notepad"], catch_exceptions=False)
        assert result.exit_code == 0
        mock_backend._resolve_hwnd.assert_called_once_with(
            app="notepad", window_title=None, hwnd=None, pid=None,
        )
        mock_backend.get_menu_items.assert_called_once_with(hwnd=12345)


# ── Platform check ───────────────────────────────────────────────────


class TestPlatformCheck:

    def test_unsupported_platform_json(self, runner):
        with _patch_platform(supports=False):
            result = runner.invoke(menu_inspect, ["--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "PLATFORM_ERROR" in result.output


# ── Backend errors ───────────────────────────────────────────────────


class TestErrors:

    def test_not_implemented_json(self, runner, mock_backend):
        mock_backend.get_menu_items.side_effect = NotImplementedError
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(menu_inspect, ["--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "NOT_SUPPORTED" in result.output

    def test_generic_error_json(self, runner, mock_backend):
        mock_backend.get_menu_items.side_effect = Exception("menu access denied")
        with _patch_platform(), _patch_backend(mock_backend):
            result = runner.invoke(menu_inspect, ["--json"], catch_exceptions=False)
        assert result.exit_code != 0
        assert "menu access denied" in result.output
