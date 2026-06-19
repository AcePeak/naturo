"""Tests for #1043: ``menu-inspect -j`` success-envelope ``count`` field.

``menu-inspect`` was the last list-returning command to omit the top-level
``count`` that the #876 -> #977 -> #980 success-envelope cleanup standardized
on. Its JSON success payload emitted ``{"success": true, "menu_items": [...]}``
with no ``count``, making it the lone outlier among the list surfaces
(``find`` / ``list windows`` / ``list screens`` all include ``count``).

These tests pin the corrected ``{success, menu_items, count}`` envelope for both
the default (tree) and ``--flat`` JSON branches, where ``count == len(menu_items)``.
They are pure CLI/JSON tests: the backend is mocked, so no DLL, desktop session,
or input simulation is required (runs identically on Linux/macOS CI).
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.core._menu import menu_inspect


def _make_menu_item(name="File", shortcut=None, submenu=None):
    """Create a mock menu item exposing the attributes ``menu_inspect`` reads."""
    item = MagicMock()
    item.name = name
    item.shortcut = shortcut
    item.enabled = True
    item.checked = False
    item.submenu = submenu or []
    item.to_dict.return_value = {"name": name, "shortcut": shortcut, "children": []}
    item.flatten.return_value = [{"path": name, "shortcut": shortcut}]
    return item


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    """Backend returning two top-level menus; the second flattens to two paths."""
    backend = MagicMock()
    file_menu = _make_menu_item(name="File")
    file_menu.flatten.return_value = [
        {"path": "File > New", "shortcut": "Ctrl+N"},
        {"path": "File > Open", "shortcut": "Ctrl+O"},
    ]
    edit_menu = _make_menu_item(name="Edit")
    edit_menu.flatten.return_value = [{"path": "Edit", "shortcut": None}]
    backend.get_menu_items.return_value = [file_menu, edit_menu]
    return backend


def _patch(mock_backend):
    return (
        patch("naturo.cli.core._common._platform_supports_gui", return_value=True),
        patch("naturo.cli.core._common._get_backend", return_value=mock_backend),
    )


class TestMenuInspectEnvelopeCount:
    def test_tree_json_has_count_matching_menu_items(self, runner, mock_backend):
        """Default (tree) JSON output reports count == len(menu_items)."""
        p_plat, p_backend = _patch(mock_backend)
        with p_plat, p_backend:
            result = runner.invoke(menu_inspect, ["--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["count"] == len(data["menu_items"])
        assert data["count"] == 2

    def test_flat_json_has_count_matching_menu_items(self, runner, mock_backend):
        """``--flat`` JSON output reports count == len(flattened menu_items)."""
        p_plat, p_backend = _patch(mock_backend)
        with p_plat, p_backend:
            result = runner.invoke(menu_inspect, ["--flat", "--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        # Two menus flatten to 2 + 1 = 3 path entries.
        assert data["count"] == len(data["menu_items"])
        assert data["count"] == 3

    def test_envelope_keys_match_list_surface_convention(self, runner, mock_backend):
        """Success keys are exactly {success, menu_items, count}, no drift."""
        p_plat, p_backend = _patch(mock_backend)
        with p_plat, p_backend:
            result = runner.invoke(menu_inspect, ["--json"], catch_exceptions=False)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert set(data.keys()) == {"success", "menu_items", "count"}
