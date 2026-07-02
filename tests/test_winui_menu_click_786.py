"""Tests for #786: WinUI 3 apps must use UIA click path for menu items.

WinUI 3 apps (Win11 Notepad, Paint) run as standalone processes, not under
ApplicationFrameHost. The UIA click path was only triggered for AFH-hosted
apps, so menu items in WinUI 3 apps were clicked via SendInput which doesn't
reliably reach XAML content.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli.interaction._click import click_cmd


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_backend():
    backend = MagicMock()
    backend.click.return_value = None
    backend.focus_window.return_value = None
    backend._resolve_hwnd.return_value = 12345
    backend._resolve_hwnds.return_value = [12345]
    backend._is_afh_window.return_value = False
    backend._is_winui_window.return_value = False
    backend.click_element_uia.return_value = True
    return backend


def _patch_backend(mock_backend):
    return patch("naturo.cli.interaction._common._get_backend", return_value=mock_backend)


def _patch_resolve_app_id(app=None, hwnd=None, pid=None):
    return patch(
        "naturo.cli.interaction._common._resolve_app_id",
        return_value=(app, hwnd, pid),
    )


def _patch_auto_route(route=None):
    return patch(
        "naturo.cli.interaction._common._auto_route",
        return_value=route or {},
    )


class TestWinuiClickDetection:
    """click must detect WinUI 3 windows and use UIA click path."""

    def test_winui_window_triggers_uia_click(self, runner, mock_backend):
        """When _is_winui_window returns True, click should try UIA path."""
        mock_backend._is_afh_window.return_value = False
        mock_backend._is_winui_window.return_value = True
        mock_backend.click_element_uia.return_value = True

        with _patch_resolve_app_id(app="notepad", hwnd=12345), \
             _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(
                click_cmd,
                ["--coords", "100", "200", "--app", "notepad"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        # UIA click path should have been used
        mock_backend.click_element_uia.assert_called_once()

    def test_non_winui_window_skips_uia(self, runner, mock_backend):
        """When neither AFH nor WinUI, normal click path is used."""
        mock_backend._is_afh_window.return_value = False
        mock_backend._is_winui_window.return_value = False

        with _patch_resolve_app_id(app="notepad", hwnd=12345), \
             _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(
                click_cmd,
                ["--coords", "100", "200", "--app", "notepad"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        # Normal click path — no UIA
        mock_backend.click.assert_called_once()
        mock_backend.click_element_uia.assert_not_called()

    def test_afh_window_still_works(self, runner, mock_backend):
        """AFH detection (original path) should still trigger UIA click."""
        mock_backend._is_afh_window.return_value = True
        mock_backend._is_winui_window.return_value = False
        mock_backend.click_element_uia.return_value = True

        with _patch_resolve_app_id(app="calculator", hwnd=12345), \
             _patch_backend(mock_backend), _patch_auto_route():
            result = runner.invoke(
                click_cmd,
                ["--coords", "100", "200", "--app", "calculator"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        mock_backend.click_element_uia.assert_called_once()


class TestIsWinuiWindow:
    """Tests for the _is_winui_window static method."""

    def test_non_windows_returns_false(self):
        from naturo.backends.windows._element import ElementMixin
        with patch("sys.platform", "linux"):
            assert ElementMixin._is_winui_window(12345) is False
