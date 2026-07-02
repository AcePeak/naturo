"""Tests for #1184: ``find`` JSON/text results must emit the reusable unified
``selector`` field that ``see`` emits for the same element.

Before #1184, ``naturo find`` returned only an ephemeral snapshot-scoped
``ref``/``id`` plus a human-readable ``breadcrumb`` — but not the machine
resolvable ``app://…`` selector — which broke the natural discover-then-save
workflow (``find`` an element → ``naturo selector save`` its selector). These
tests pin that:

1. Every ``find`` JSON element carries a non-empty ``app://`` ``selector``.
2. ``find`` and ``see`` emit an *identical* selector for the same node
   (the core parity contract).
3. The selector survives the lateral payload-builder paths
   (``--all`` / ``--role`` / ``--actionable``) and the human-readable output.

The fixture is a small hermetic UIA-shaped tree; no real desktop is needed, so
these run on headless CI (same backend ``ElementInfo`` consumed by both
commands, mocked at ``_get_backend``).
"""

import json

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from naturo.backends.base import ElementInfo
from naturo.cli.core._find import find_cmd
from naturo.cli.core._see import see


def _node(role, name, children=None, el_id=""):
    """Build a backend ElementInfo node for the fixture tree."""
    return ElementInfo(
        id=el_id,
        role=role,
        name=name,
        value=None,
        x=10,
        y=20,
        width=100,
        height=40,
        children=children or [],
        properties={},
    )


@pytest.fixture
def fixture_tree():
    """A Notepad-shaped tree: Window > Pane > Document, plus a Save Button.

    Mirrors the #1184 repro (a Document nested under a Pane under the Window),
    so the threaded ancestor chain (Window, Pane) is exercised when the unified
    selector is rebuilt for the Document.
    """
    document = _node("Document", "文本编辑器")
    pane = _node("Pane", "", children=[document])
    save_button = _node("Button", "Save", el_id="SaveBtn")
    window = _node("Window", "无标题 - Notepad", children=[pane, save_button])
    return window


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend(fixture_tree):
    """Mock the backend so both find and see resolve the fixture tree."""
    mock_be = MagicMock()
    mock_be.get_element_tree.return_value = fixture_tree
    # see builds a JSON dpi_context from these; keep them serializable so the
    # only thing under test is the selector (not the mock's stand-in objects).
    mock_be.get_dpi_scale.return_value = 1.0
    mock_be.list_monitors.return_value = []
    with patch("naturo.cli.core._common._platform_supports_gui", return_value=True), \
         patch("naturo.cli.core._common._get_backend", return_value=mock_be):
        yield mock_be


def _find_json(runner, *args):
    """Invoke find --json and return the parsed payload."""
    result = runner.invoke(find_cmd, list(args) + ["--json"])
    assert result.exit_code == 0, f"find failed: {result.output}"
    return json.loads(result.output)


def _walk(node):
    """Yield every node in a see JSON tree (depth-first)."""
    yield node
    for child in node.get("children", []):
        yield from _walk(child)


class TestFindEmitsSelector:
    """find JSON results must include the reusable unified selector (#1184)."""

    def test_query_result_has_selector(self, runner, mock_backend):
        """A query-search match carries a non-empty app:// selector."""
        payload = _find_json(runner, "role:Document", "--hwnd", "12345")
        assert payload["success"] is True
        assert payload["count"] == 1
        element = payload["elements"][0]
        assert "selector" in element, "find element payload omits 'selector'"
        assert element["selector"].startswith("app://"), element["selector"]
        # The full ancestor chain (Window > Pane > Document) is encoded.
        assert "Document" in element["selector"]
        assert "Window" in element["selector"]

    def test_selector_is_resolvable_not_breadcrumb_prose(self, runner, mock_backend):
        """selector must be a machine-resolvable URI, distinct from breadcrumb."""
        element = _find_json(runner, "role:Document", "--hwnd", "12345")["elements"][0]
        # breadcrumb is human prose ("Window:… > Pane > Document:…");
        # selector is an app:// URI — they must not be the same string.
        assert element["selector"] != element["breadcrumb"]
        assert " > " not in element["selector"]

    @pytest.mark.parametrize("extra_args", [
        ["--all"],
        ["--role", "Button"],
        ["--all", "--actionable"],
    ])
    def test_lateral_payload_paths_include_selector(self, runner, mock_backend, extra_args):
        """--all / --role / --actionable share the payload builder — all must carry selector."""
        payload = _find_json(runner, "--hwnd", "12345", *extra_args)
        assert payload["count"] >= 1
        for element in payload["elements"]:
            assert element.get("selector", "").startswith("app://"), element

    def test_human_output_shows_selector(self, runner, mock_backend):
        """The non-JSON human output is also discover-then-save friendly."""
        result = runner.invoke(find_cmd, ["role:Document", "--hwnd", "12345"])
        assert result.exit_code == 0, result.output
        assert "selector: app://" in result.output


class TestFindSeeSelectorParity:
    """find and see must emit an IDENTICAL selector for the same element (#1184)."""

    def test_find_selector_matches_see_selector(self, runner, mock_backend):
        """The Document's find selector equals its see selector, byte-for-byte."""
        # find side
        find_element = _find_json(runner, "role:Document", "--hwnd", "12345")["elements"][0]
        find_selector = find_element["selector"]

        # see side — same backend tree, same --hwnd targeting so both default
        # the selector app to "*" and walk the identical ancestor chain.
        see_result = runner.invoke(see, ["--hwnd", "12345", "--json", "--no-snapshot"])
        assert see_result.exit_code == 0, see_result.output
        see_tree = json.loads(see_result.output)
        document_nodes = [
            n for n in _walk(see_tree)
            if n.get("role") == "Document" and n.get("name") == "文本编辑器"
        ]
        assert len(document_nodes) == 1, "see did not surface the Document node"
        see_selector = document_nodes[0]["selector"]

        assert find_selector == see_selector, (
            f"find/see selector mismatch:\n  find={find_selector}\n  see ={see_selector}"
        )
