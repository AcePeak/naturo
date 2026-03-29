"""Tests for CDP integration in cascade engine and CDPClient.get_interactive_elements.

These tests use full mock coverage and do NOT require a desktop or browser.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from naturo.backends.base import ElementInfo
from naturo.cdp import CDPClient, CDPError


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_element(
    id: str = "e1",
    role: str = "Button",
    name: str = "OK",
    x: int = 100,
    y: int = 100,
    width: int = 80,
    height: int = 30,
    children: list | None = None,
    properties: dict | None = None,
) -> ElementInfo:
    return ElementInfo(
        id=id, role=role, name=name, value=None,
        x=x, y=y, width=width, height=height,
        children=children or [],
        properties=properties or {},
    )


def _mock_cdp_ws_client(evaluate_result):
    """Create a CDPClient with mocked WebSocket that returns evaluate_result."""
    client = CDPClient(port=9222)
    mock_ws = MagicMock()
    mock_ws.connected = True
    mock_ws.recv.return_value = json.dumps({
        "id": 1,
        "result": {"result": {"type": "object", "value": evaluate_result}},
    })
    client._ws = mock_ws
    return client


# ── CDPClient.get_interactive_elements ───────────────────────────────────────


class TestGetInteractiveElements:
    """Test the get_interactive_elements method on CDPClient."""

    def test_returns_elements_with_bounds(self):
        elements = [
            {
                "tagName": "button",
                "role": "button",
                "name": "Submit",
                "value": None,
                "bounds": {"x": 10, "y": 20, "width": 100, "height": 30},
                "selector": "button#submit",
                "nodeIndex": 0,
            },
            {
                "tagName": "input",
                "role": "textbox",
                "name": "Email",
                "value": "user@example.com",
                "bounds": {"x": 10, "y": 60, "width": 200, "height": 25},
                "selector": "input#email",
                "nodeIndex": 1,
            },
        ]
        client = _mock_cdp_ws_client(elements)
        result = client.get_interactive_elements()

        assert len(result) == 2
        assert result[0]["tagName"] == "button"
        assert result[0]["name"] == "Submit"
        assert result[0]["bounds"]["width"] == 100
        assert result[1]["value"] == "user@example.com"

    def test_returns_empty_list_on_none(self):
        client = _mock_cdp_ws_client(None)
        result = client.get_interactive_elements()
        assert result == []

    def test_returns_empty_list_on_non_list(self):
        client = _mock_cdp_ws_client("not a list")
        result = client.get_interactive_elements()
        assert result == []

    def test_custom_selector(self):
        client = _mock_cdp_ws_client([])
        result = client.get_interactive_elements(selector="div.custom")
        assert result == []
        # Verify the custom selector was passed in the JS
        sent = json.loads(client._ws.send.call_args[0][0])
        assert "div.custom" in sent["params"]["expression"]

    def test_not_connected_raises(self):
        client = CDPClient()
        with pytest.raises(CDPError, match="Not connected"):
            client.get_interactive_elements()


# ── cascade._fetch_cdp_elements ──────────────────────────────────────────────


class TestFetchCdpElements:
    """Test cascade._fetch_cdp_elements with mocked CDPClient."""

    def test_fetches_and_converts_elements(self):
        mock_elements = [
            {
                "tagName": "button",
                "role": "button",
                "name": "Sign In",
                "value": None,
                "bounds": {"x": 50, "y": 100, "width": 120, "height": 35},
                "selector": "button.login",
                "nodeIndex": 0,
            },
            {
                "tagName": "a",
                "role": "link",
                "name": "Forgot Password",
                "value": None,
                "bounds": {"x": 50, "y": 150, "width": 100, "height": 20},
                "selector": "a.forgot",
                "nodeIndex": 1,
            },
        ]

        mock_client = MagicMock()
        mock_client.get_interactive_elements.return_value = mock_elements

        with patch("naturo.cdp.CDPClient", return_value=mock_client):
            from naturo.cascade import _fetch_cdp_elements

            results = _fetch_cdp_elements(
                pid=1234,
                debug_port=9222,
                parent_bounds=(100, 200, 800, 600),
            )

        assert len(results) == 2

        btn = results[0]
        assert btn.role == "Button"
        assert btn.name == "Sign In"
        # Bounds offset by parent_bounds (100, 200)
        assert btn.x == 150  # 50 + 100
        assert btn.y == 300  # 100 + 200
        assert btn.width == 120
        assert btn.height == 35
        assert btn.properties["source"] == "cdp"
        assert btn.properties["tag"] == "button"
        assert btn.properties["css_selector"] == "button.login"

        link = results[1]
        assert link.role == "Link"
        assert link.name == "Forgot Password"

    def test_skips_zero_dimension_elements(self):
        mock_elements = [
            {
                "tagName": "div",
                "role": "",
                "name": "",
                "value": None,
                "bounds": {"x": 0, "y": 0, "width": 0, "height": 0},
                "selector": "div",
                "nodeIndex": 0,
            },
        ]

        mock_client = MagicMock()
        mock_client.get_interactive_elements.return_value = mock_elements

        with patch("naturo.cdp.CDPClient", return_value=mock_client):
            from naturo.cascade import _fetch_cdp_elements

            results = _fetch_cdp_elements(
                pid=1234, debug_port=9222, parent_bounds=(0, 0, 800, 600),
            )

        assert len(results) == 0

    def test_returns_empty_on_connection_error(self):
        mock_client = MagicMock()
        mock_client.connect.side_effect = Exception("Connection refused")

        with patch("naturo.cdp.CDPClient", return_value=mock_client):
            from naturo.cascade import _fetch_cdp_elements

            results = _fetch_cdp_elements(
                pid=1234, debug_port=9222, parent_bounds=(0, 0, 800, 600),
            )

        assert results == []

    def test_role_mapping_fallback(self):
        """When role is empty, falls back to tag-based role mapping."""
        mock_elements = [
            {
                "tagName": "input",
                "role": "",
                "name": "Username",
                "value": "",
                "bounds": {"x": 10, "y": 10, "width": 200, "height": 25},
                "selector": "input#user",
                "nodeIndex": 0,
            },
            {
                "tagName": "select",
                "role": "",
                "name": "Country",
                "value": "US",
                "bounds": {"x": 10, "y": 50, "width": 200, "height": 25},
                "selector": "select#country",
                "nodeIndex": 1,
            },
        ]

        mock_client = MagicMock()
        mock_client.get_interactive_elements.return_value = mock_elements

        with patch("naturo.cdp.CDPClient", return_value=mock_client):
            from naturo.cascade import _fetch_cdp_elements

            results = _fetch_cdp_elements(
                pid=1, debug_port=9222, parent_bounds=(0, 0, 800, 600),
            )

        assert results[0].role == "Edit"      # input → Edit
        assert results[1].role == "ComboBox"   # select → ComboBox


# ── cascade.find_cdp_port ────────────────────────────────────────────────────


class TestFindCdpPort:
    """Test the find_cdp_port utility."""

    def test_finds_port_via_http_probe(self):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            from naturo.cascade import find_cdp_port

            port = find_cdp_port(pid=None)

        assert port == 9222

    def test_returns_none_when_no_port_responds(self):
        with patch("urllib.request.urlopen", side_effect=Exception("refused")):
            from naturo.cascade import find_cdp_port

            port = find_cdp_port(pid=None)

        assert port is None

    @patch("platform.system", return_value="Linux")
    def test_skips_wmic_on_linux(self, mock_sys):
        """On non-Windows, skip command-line parsing and go straight to probing."""
        with patch("urllib.request.urlopen", side_effect=Exception("refused")):
            from naturo.cascade import find_cdp_port

            port = find_cdp_port(pid=1234)

        assert port is None


# ── cascade._run_cdp_only ────────────────────────────────────────────────────


class TestRunCdpOnly:
    """Test the CDP-only cascade mode (--backend cdp)."""

    def test_returns_error_when_no_port(self):
        with patch("naturo.cascade.find_cdp_port", return_value=None):
            from naturo.cascade import _run_cdp_only

            mock_backend = MagicMock()
            result = _run_cdp_only(mock_backend, app="chrome")

        assert result.tree is None
        assert result.primary_provider == "cdp"
        assert result.stats.providers[0].status == "error"

    def test_merges_uia_and_cdp_elements(self):
        uia_tree = _make_element(
            id="root", role="Window", name="Google Chrome",
            x=0, y=0, width=1920, height=1080,
            children=[
                _make_element(id="e1", role="ToolBar", name="Main toolbar",
                              x=0, y=0, width=1920, height=60),
            ],
        )

        cdp_elements = [
            _make_element(id="cdp_0", role="Button", name="Search",
                          x=100, y=200, width=80, height=30,
                          properties={"source": "cdp", "tag": "button",
                                      "css_selector": "button.search",
                                      "parent_id": None}),
        ]

        mock_backend = MagicMock()
        mock_backend.get_element_tree.return_value = uia_tree

        with (
            patch("naturo.cascade.find_cdp_port", return_value=9222),
            patch("naturo.cascade._fetch_cdp_elements", return_value=cdp_elements),
        ):
            from naturo.cascade import _run_cdp_only

            result = _run_cdp_only(mock_backend, app="chrome", pid=1234)

        assert result.tree is not None
        assert result.primary_provider == "cdp"
        # UIA elements + CDP elements merged
        assert len(result.tree.children) == 2  # toolbar + cdp button
        # CDP element is tagged
        cdp_child = result.tree.children[1]
        assert cdp_child.properties.get("source") == "cdp"

    def test_creates_synthetic_root_without_uia(self):
        """When UIA fails, CDP elements still get a synthetic root."""
        cdp_elements = [
            _make_element(id="cdp_0", role="Button", name="Login",
                          x=50, y=100, width=100, height=30,
                          properties={"source": "cdp"}),
        ]

        mock_backend = MagicMock()
        mock_backend.get_element_tree.side_effect = Exception("No UIA")

        with (
            patch("naturo.cascade.find_cdp_port", return_value=9222),
            patch("naturo.cascade._fetch_cdp_elements", return_value=cdp_elements),
        ):
            from naturo.cascade import _run_cdp_only

            result = _run_cdp_only(mock_backend, app="chrome", pid=1234)

        assert result.tree is not None
        assert result.tree.role == "Window"
        assert len(result.tree.children) == 1
        assert result.tree.children[0].name == "Login"


# ── cascade.run_cascade with CDP enrichment ──────────────────────────────────


class TestRunCascadeWithCdp:
    """Test that run_cascade properly enriches UIA tree with CDP elements."""

    def test_auto_mode_tries_cdp_after_uia(self):
        uia_tree = _make_element(
            id="root", role="Window", name="Slack",
            x=0, y=0, width=1920, height=1080,
            children=[
                _make_element(id="e1", role="Pane", name="Content",
                              x=0, y=60, width=1920, height=1020),
            ],
        )

        cdp_elements = [
            _make_element(id="cdp_0", role="Button", name="Send",
                          x=100, y=500, width=80, height=30,
                          properties={"source": "cdp"}),
        ]

        mock_backend = MagicMock()
        mock_backend.get_element_tree.return_value = uia_tree

        with (
            patch("naturo.cascade.find_cdp_port", return_value=9222),
            patch("naturo.cascade._fetch_cdp_elements", return_value=cdp_elements),
        ):
            from naturo.cascade import run_cascade

            result = run_cascade(
                mock_backend,
                app="slack",
                pid=5678,
                backend_name="auto",
            )

        assert result.tree is not None
        # Check that CDP provider was attempted
        cdp_providers = [p for p in result.stats.providers if p.name == "cdp"]
        assert len(cdp_providers) == 1
        assert cdp_providers[0].elements == 1

    def test_cdp_backend_routes_to_cdp_only(self):
        """--backend cdp should use _run_cdp_only path."""
        mock_backend = MagicMock()
        mock_backend.get_element_tree.return_value = _make_element(
            id="root", role="Window", name="Chrome",
            x=0, y=0, width=1920, height=1080,
        )

        with (
            patch("naturo.cascade.find_cdp_port", return_value=9222),
            patch("naturo.cascade._fetch_cdp_elements", return_value=[]),
        ):
            from naturo.cascade import run_cascade

            result = run_cascade(
                mock_backend,
                app="chrome",
                pid=1234,
                backend_name="cdp",
            )

        assert result.primary_provider == "cdp"
