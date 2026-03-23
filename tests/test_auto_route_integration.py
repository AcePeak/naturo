"""Tests for _auto_route helper in interaction commands."""
import pytest
from unittest.mock import MagicMock, patch

from naturo.cli.interaction import _auto_route


class TestAutoRoute:
    """Tests for the _auto_route helper function."""

    def test_no_app_no_pid_returns_empty(self):
        """When no app/pid specified, returns empty dict (no routing)."""
        result = _auto_route(app=None, pid=None, method="auto", json_output=False)
        assert result == {}

    def test_explicit_method_returns_empty(self):
        """When method is explicit (not auto), returns empty dict."""
        result = _auto_route(app="Notepad", pid=None, method="uia", json_output=False)
        assert result == {}

    @patch("naturo.routing.resolve_method")
    def test_auto_with_app_calls_routing(self, mock_resolve):
        """When method=auto and app is set, calls resolve_method."""
        from naturo.routing import RoutingResult

        mock_resolve.return_value = RoutingResult(
            pid=1234,
            app_name="notepad.exe",
            method="uia",
            source="auto",
            framework="win32",
            confidence=0.9,
        )

        result = _auto_route(app="Notepad", pid=None, method="auto", json_output=False)
        assert result["method"] == "uia"
        assert result["framework"] == "win32"
        assert result["pid"] == 1234
        mock_resolve.assert_called_once_with(app="Notepad", pid=None, explicit_method="auto")

    @patch("naturo.routing.resolve_method")
    def test_auto_with_pid_calls_routing(self, mock_resolve):
        """When method=auto and pid is set, calls resolve_method."""
        from naturo.routing import RoutingResult

        mock_resolve.return_value = RoutingResult(
            pid=5678,
            app_name="",
            method="cdp",
            source="auto",
            framework="electron",
            confidence=0.85,
        )

        result = _auto_route(app=None, pid=5678, method="auto", json_output=True)
        assert result["method"] == "cdp"
        assert result["source"] == "auto"
        mock_resolve.assert_called_once_with(app=None, pid=5678, explicit_method="auto")

    @patch("naturo.routing.resolve_method")
    def test_routing_exception_returns_empty(self, mock_resolve):
        """When routing raises an exception, returns empty dict gracefully."""
        mock_resolve.side_effect = ImportError("module not found")

        result = _auto_route(app="SomeApp", pid=None, method="auto", json_output=False)
        assert result == {}

    def test_explicit_method_no_app_returns_empty(self):
        """Explicit method with no app returns empty dict."""
        result = _auto_route(app=None, pid=None, method="cdp", json_output=False)
        assert result == {}
