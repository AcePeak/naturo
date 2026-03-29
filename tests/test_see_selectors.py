"""Tests for unified selector output in the see command (#102).

Verifies that:
- JSON mode always includes a 'selector' field on each element
- Text mode shows selectors when --selectors flag is used
- Selector URIs use the correct app name and element attributes
- Ancestor chain is correctly propagated for nested selectors
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.backends.base import ElementInfo


def _make_tree() -> ElementInfo:
    """Build a simple UI tree for testing selector output."""
    child_button = ElementInfo(
        id="btnSave", role="Button", name="Save",
        value=None, x=100, y=200, width=80, height=30,
        children=[], properties={},
    )
    child_edit = ElementInfo(
        id="txtInput", role="Edit", name="Search",
        value="hello", x=50, y=50, width=400, height=25,
        children=[], properties={},
    )
    child_text = ElementInfo(
        id="", role="Text", name="Status Bar",
        value=None, x=0, y=580, width=800, height=20,
        children=[], properties={},
    )
    root = ElementInfo(
        id="mainWindow", role="Window", name="Test App",
        value=None, x=0, y=0, width=800, height=600,
        children=[child_button, child_edit, child_text],
        properties={},
    )
    return root


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.get_element_tree.return_value = _make_tree()
    backend.list_monitors.return_value = []
    backend.get_dpi_scale.return_value = 1.0
    return backend


def _invoke_see(runner, mock_backend, args):
    """Invoke the see command with mocked backend and platform."""
    from naturo.cli.core import see
    with patch("naturo.cli.core._common._get_backend", return_value=mock_backend), \
         patch("naturo.cli.core._common._platform_supports_gui", return_value=True):
        return runner.invoke(see, args)


class TestSeeSelectorsJSON:
    """JSON mode always includes selector field."""

    def test_json_output_has_selector_field(self, runner, mock_backend):
        result = _invoke_see(runner, mock_backend, ["--json", "--no-snapshot"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output.strip())
        assert "selector" in data
        assert data["selector"].startswith("app://")

    def test_json_selector_uses_app_name(self, runner, mock_backend):
        mock_backend._resolve_hwnds = MagicMock(return_value=[12345])
        mock_backend.get_element_tree.return_value = _make_tree()
        result = _invoke_see(runner, mock_backend,
                             ["--json", "--no-snapshot", "--app", "notepad"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output.strip())
        # Root is the virtual "Application" node wrapping per-window trees
        # when --app resolves multiple HWNDs; check children
        assert "notepad" in data["selector"]

    def test_json_selector_defaults_to_wildcard(self, runner, mock_backend):
        result = _invoke_see(runner, mock_backend, ["--json", "--no-snapshot"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output.strip())
        assert data["selector"].startswith("app://*/")

    def test_json_children_have_selectors(self, runner, mock_backend):
        result = _invoke_see(runner, mock_backend, ["--json", "--no-snapshot"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output.strip())
        children = data["children"]
        assert len(children) == 3

        # Button with automationid "btnSave"
        btn = children[0]
        assert "selector" in btn
        assert "btnSave" in btn["selector"]

        # Edit with automationid "txtInput"
        edit = children[1]
        assert "selector" in edit
        assert "txtInput" in edit["selector"]

    def test_json_selector_includes_ancestor_context(self, runner, mock_backend):
        """Selectors for children include discriminating ancestors."""
        result = _invoke_see(runner, mock_backend, ["--json", "--no-snapshot"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output.strip())
        btn = data["children"][0]
        # Child selector should reference ancestor Window in path
        assert "Window" in btn["selector"]
        assert "Button" in btn["selector"]

    def test_json_selector_name_fallback_when_no_aid(self, runner, mock_backend):
        """Elements without automationid use name in selector."""
        result = _invoke_see(runner, mock_backend, ["--json", "--no-snapshot"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output.strip())
        text_el = data["children"][2]  # Text "Status Bar" with id=""
        assert "selector" in text_el
        assert "Status Bar" in text_el["selector"]


class TestSeeSelectorsText:
    """Text mode shows selectors with --selectors flag."""

    def test_text_no_selectors_by_default(self, runner, mock_backend):
        result = _invoke_see(runner, mock_backend, ["--no-snapshot"])
        assert result.exit_code == 0, result.output
        assert "app://" not in result.output

    def test_text_selectors_flag_shows_uris(self, runner, mock_backend):
        result = _invoke_see(runner, mock_backend, ["--no-snapshot", "--selectors"])
        assert result.exit_code == 0, result.output
        assert "app://" in result.output

    def test_text_selectors_with_app(self, runner, mock_backend):
        result = _invoke_see(runner, mock_backend,
                             ["--no-snapshot", "--selectors", "--app", "notepad"])
        assert result.exit_code == 0, result.output
        assert "app://notepad/" in result.output

    def test_text_selectors_tip_message(self, runner, mock_backend):
        """When --selectors is used, tip mentions --selector for stable targeting."""
        result = _invoke_see(runner, mock_backend, ["--selectors"])
        assert result.exit_code == 0, result.output
        assert "--selector" in result.output


class TestSeeSelectorsHelp:
    """The --selectors flag is documented in --help."""

    def test_selectors_option_in_help(self, runner):
        from naturo.cli.core import see
        result = runner.invoke(see, ["--help"])
        assert result.exit_code == 0
        assert "--selectors" in result.output
        assert "unified selectors" in result.output.lower()
