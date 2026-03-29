"""Tests for --app validation in action commands (#565).

When --app is explicitly provided but the app is not running, all action
commands (click, type, press, hotkey) must exit with code 1 instead of
silently falling back to vision-based desktop interaction.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from naturo.routing import RoutingResult


class TestAutoRouteAppNotFound:
    """_auto_route must error when --app is specified but not found (#565)."""

    @patch("naturo.cli.interaction._common._get_backend")
    def test_click_nonexistent_app_coords_fails(self, mock_get_backend):
        """click --app doesnotexist --coords 100 100 must exit with code 1."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        backend = MagicMock()
        mock_get_backend.return_value = backend

        route_result = RoutingResult(
            app_name="doesnotexist",
            method="vision",
            source="auto",
            pid=None,
        )

        runner = CliRunner()
        with patch(
            "naturo.routing.resolve_method", return_value=route_result
        ):
            result = runner.invoke(click_cmd, [
                "--coords", "100", "100",
                "--app", "doesnotexist",
                "--no-verify",
            ])

        assert result.exit_code != 0, (
            f"Expected non-zero exit code, got {result.exit_code}. "
            f"Output: {result.output}"
        )
        assert "not found" in result.output.lower() or "not found" in (result.output or "").lower()

    @patch("naturo.cli.interaction._common._get_backend")
    def test_click_nonexistent_app_coords_json_fails(self, mock_get_backend):
        """click --app doesnotexist --coords 100 100 --json must return error."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        backend = MagicMock()
        mock_get_backend.return_value = backend

        route_result = RoutingResult(
            app_name="doesnotexist",
            method="vision",
            source="auto",
            pid=None,
        )

        runner = CliRunner()
        with patch(
            "naturo.routing.resolve_method", return_value=route_result
        ):
            result = runner.invoke(click_cmd, [
                "--coords", "100", "100",
                "--app", "doesnotexist",
                "--no-verify",
                "--json",
            ])

        assert result.exit_code != 0
        assert "APP_NOT_FOUND" in (result.output or "")

    @patch("naturo.cli.interaction._common._get_backend")
    def test_click_valid_app_coords_proceeds(self, mock_get_backend):
        """click --app notepad --coords 100 100 must proceed when app exists."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        backend = MagicMock()
        mock_get_backend.return_value = backend

        route_result = RoutingResult(
            pid=1234,
            app_name="notepad.exe",
            method="uia",
            source="auto",
            framework="win32",
            confidence=0.9,
        )

        runner = CliRunner()
        with patch(
            "naturo.routing.resolve_method", return_value=route_result
        ):
            result = runner.invoke(click_cmd, [
                "--coords", "100", "100",
                "--app", "notepad",
                "--no-verify",
            ])

        # Should not contain "not found" error
        assert "not found" not in (result.output or "").lower() or result.exit_code == 0

    @patch("naturo.cli.interaction._common._get_backend")
    def test_click_no_app_flag_no_validation(self, mock_get_backend):
        """click --coords 100 100 (no --app) must proceed without validation."""
        from click.testing import CliRunner
        from naturo.cli.interaction import click_cmd

        backend = MagicMock()
        mock_get_backend.return_value = backend

        runner = CliRunner()
        # No --app flag, so no routing at all — should not error
        result = runner.invoke(click_cmd, [
            "--coords", "100", "100",
            "--no-verify",
        ])

        # Should not fail with app-not-found
        assert "not found" not in (result.output or "").lower()

    @patch("naturo.cli.interaction._common._get_backend")
    def test_type_nonexistent_app_fails(self, mock_get_backend):
        """type --app doesnotexist must also fail (#565 affects all actions)."""
        from click.testing import CliRunner
        from naturo.cli.interaction import type_cmd

        backend = MagicMock()
        mock_get_backend.return_value = backend

        route_result = RoutingResult(
            app_name="doesnotexist",
            method="vision",
            source="auto",
            pid=None,
        )

        runner = CliRunner()
        with patch(
            "naturo.routing.resolve_method", return_value=route_result
        ):
            result = runner.invoke(type_cmd, [
                "hello",
                "--app", "doesnotexist",
                "--no-verify",
            ])

        assert result.exit_code != 0
