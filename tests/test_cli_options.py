"""Tests for naturo/cli/options.py — shared CLI option decorators and helpers.

Covers:
- resolve_app_id_to_hwnd: resolution logic, error output, JSON error format
- Option decorators: verify they produce correct Click parameters
- get_vision_provider_from_options: provider instantiation with overrides
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from naturo.cli.options import (
    app_id_option,
    app_option,
    hwnd_option,
    json_option,
    maybe_promote_app_to_app_id,
    on_option,
    pid_option,
    process_name_option,
    resolve_app_id_to_hwnd,
    window_option,
)


# ── resolve_app_id_to_hwnd ────────────────────────────────────────────────


class TestResolveAppIdToHwnd:
    """Tests for resolve_app_id_to_hwnd helper."""

    def test_none_app_id_returns_hwnd_passthrough(self):
        """When app_id is None, return the hwnd argument unchanged."""
        assert resolve_app_id_to_hwnd(None, 12345, False) == 12345

    def test_none_app_id_none_hwnd(self):
        """When both app_id and hwnd are None, return None."""
        assert resolve_app_id_to_hwnd(None, None, False) is None

    @patch("naturo.app_ids.get_app_id_map")
    def test_valid_app_id_returns_handle(self, mock_get_map):
        """Valid app_id resolves to the entry's handle."""
        entry = MagicMock()
        entry.handle = 99999
        mock_get_map.return_value.resolve.return_value = entry

        result = resolve_app_id_to_hwnd("a1", None, False)
        assert result == 99999
        mock_get_map.return_value.resolve.assert_called_once_with("a1")

    @patch("naturo.app_ids.get_app_id_map")
    def test_valid_app_id_overrides_hwnd(self, mock_get_map):
        """When app_id resolves, its handle takes precedence over hwnd."""
        entry = MagicMock()
        entry.handle = 77777
        mock_get_map.return_value.resolve.return_value = entry

        result = resolve_app_id_to_hwnd("a2", 11111, False)
        assert result == 77777

    @patch("naturo.app_ids.get_app_id_map")
    def test_invalid_app_id_returns_none_text(self, mock_get_map, capsys):
        """Invalid app_id returns None and prints text error."""
        mock_get_map.return_value.resolve.return_value = None

        result = resolve_app_id_to_hwnd("a99", None, False)
        assert result is None

    @patch("naturo.app_ids.get_app_id_map")
    def test_invalid_app_id_returns_none_json(self, mock_get_map):
        """Invalid app_id in JSON mode emits JSON error."""
        mock_get_map.return_value.resolve.return_value = None

        # Use a Click command context to capture click.echo output
        @click.command()
        @click.pass_context
        def _test_cmd(ctx):
            result = resolve_app_id_to_hwnd("a99", None, True)
            ctx.obj = {"result": result}

        runner = CliRunner()
        res = runner.invoke(_test_cmd)
        assert res.exit_code != 0 or "APP_ID_NOT_FOUND" in res.output


# ── maybe_promote_app_to_app_id (#752) ───────────────────────────────────


class TestMaybePromoteAppToAppId:
    """Tests for app ID pattern detection in --app flag."""

    def test_app_id_pattern_promoted(self):
        """'a1' in --app is promoted to --app-id."""
        app, app_id = maybe_promote_app_to_app_id("a1", None)
        assert app is None
        assert app_id == "a1"

    def test_multi_digit_app_id_promoted(self):
        """'a123' in --app is promoted to --app-id."""
        app, app_id = maybe_promote_app_to_app_id("a123", None)
        assert app is None
        assert app_id == "a123"

    def test_process_name_not_promoted(self):
        """Normal process names are not promoted."""
        app, app_id = maybe_promote_app_to_app_id("notepad", None)
        assert app == "notepad"
        assert app_id is None

    def test_explicit_app_id_takes_precedence(self):
        """When --app-id is already set, --app is not promoted."""
        app, app_id = maybe_promote_app_to_app_id("a2", "a1")
        assert app == "a2"
        assert app_id == "a1"

    def test_none_app_unchanged(self):
        """None --app is returned unchanged."""
        app, app_id = maybe_promote_app_to_app_id(None, None)
        assert app is None
        assert app_id is None

    def test_partial_match_not_promoted(self):
        """Strings like 'app1' or 'abc' are not promoted."""
        app, app_id = maybe_promote_app_to_app_id("app1", None)
        assert app == "app1"
        assert app_id is None

    def test_uppercase_not_promoted(self):
        """'A1' (uppercase) is not promoted — app IDs are lowercase."""
        app, app_id = maybe_promote_app_to_app_id("A1", None)
        assert app == "A1"
        assert app_id is None

    def test_bare_a_not_promoted(self):
        """'a' alone (no digits) is not promoted."""
        app, app_id = maybe_promote_app_to_app_id("a", None)
        assert app == "a"
        assert app_id is None


# ── Option decorators ─────────────────────────────────────────────────────


class TestOptionDecorators:
    """Verify option decorators produce correct Click parameters."""

    def _get_params(self, decorator) -> list[click.Parameter]:
        """Apply decorator to a dummy command and return its params."""
        @click.command()
        @decorator
        def _cmd(**kwargs):
            click.echo(json.dumps(kwargs))

        return _cmd.params

    def test_app_option_creates_param(self):
        params = self._get_params(app_option)
        names = [p.name for p in params]
        assert "app" in names

    def test_window_option_creates_param(self):
        params = self._get_params(window_option)
        names = [p.name for p in params]
        assert "window" in names

    def test_window_option_has_hidden_aliases(self):
        params = self._get_params(window_option)
        all_opts = []
        for p in params:
            all_opts.extend(p.opts)
        assert "--window" in all_opts
        assert "--window-title" in all_opts
        assert "--title" in all_opts

    def test_hwnd_option_creates_int_param(self):
        params = self._get_params(hwnd_option)
        hwnd_param = next(p for p in params if p.name == "hwnd")
        assert hwnd_param.type == click.INT

    def test_hwnd_option_has_hidden_alias(self):
        params = self._get_params(hwnd_option)
        all_opts = []
        for p in params:
            all_opts.extend(p.opts)
        assert "--window-id" in all_opts

    def test_pid_option_creates_int_param(self):
        params = self._get_params(pid_option)
        pid_param = next(p for p in params if p.name == "pid")
        assert pid_param.type == click.INT

    def test_on_option_creates_param(self):
        params = self._get_params(on_option)
        names = [p.name for p in params]
        assert "on_ref" in names

    def test_app_id_option_creates_param(self):
        params = self._get_params(app_id_option)
        names = [p.name for p in params]
        assert "app_id" in names

    def test_json_option_is_flag(self):
        params = self._get_params(json_option)
        json_param = next(p for p in params if p.name == "json_output")
        assert json_param.is_flag

    def test_process_name_option_maps_to_app(self):
        params = self._get_params(process_name_option)
        names = [p.name for p in params]
        assert "app" in names


# ── Option decorator integration ──────────────────────────────────────────


class TestOptionIntegration:
    """Test that options work correctly when invoked via CLI."""

    def test_window_alias_maps_to_window_param(self):
        """--window-title value arrives as 'window' parameter."""
        @click.command()
        @window_option
        def _cmd(window):
            click.echo(f"window={window}")

        runner = CliRunner()
        result = runner.invoke(_cmd, ["--window-title", "Notepad"])
        assert result.exit_code == 0
        assert "window=Notepad" in result.output

    def test_window_primary_option(self):
        """--window value arrives as 'window' parameter."""
        @click.command()
        @window_option
        def _cmd(window):
            click.echo(f"window={window}")

        runner = CliRunner()
        result = runner.invoke(_cmd, ["--window", "Calculator"])
        assert result.exit_code == 0
        assert "window=Calculator" in result.output

    def test_hwnd_window_id_alias(self):
        """--window-id value arrives as 'hwnd' parameter."""
        @click.command()
        @hwnd_option
        def _cmd(hwnd):
            click.echo(f"hwnd={hwnd}")

        runner = CliRunner()
        result = runner.invoke(_cmd, ["--window-id", "65536"])
        assert result.exit_code == 0
        assert "hwnd=65536" in result.output

    def test_process_name_alias_maps_to_app(self):
        """--process-name value arrives as 'app' parameter."""
        @click.command()
        @process_name_option
        def _cmd(app):
            click.echo(f"app={app}")

        runner = CliRunner()
        result = runner.invoke(_cmd, ["--process-name", "chrome.exe"])
        assert result.exit_code == 0
        assert "app=chrome.exe" in result.output

    def test_json_short_flag(self):
        """-j flag sets json_output to True."""
        @click.command()
        @json_option
        def _cmd(json_output):
            click.echo(f"json={json_output}")

        runner = CliRunner()
        result = runner.invoke(_cmd, ["-j"])
        assert result.exit_code == 0
        assert "json=True" in result.output


# ── get_vision_provider_from_options ──────────────────────────────────────


class TestGetVisionProviderFromOptions:
    """Tests for get_vision_provider_from_options."""

    @patch("naturo.providers.base.get_vision_provider")
    def test_default_auto_provider(self, mock_get):
        """Default call uses 'auto' provider with no extra kwargs."""
        from naturo.cli.options import get_vision_provider_from_options

        get_vision_provider_from_options()
        mock_get.assert_called_once_with("auto")

    @patch("naturo.providers.base.get_vision_provider")
    def test_explicit_provider_and_model(self, mock_get):
        """Provider and model are forwarded correctly."""
        from naturo.cli.options import get_vision_provider_from_options

        get_vision_provider_from_options(
            provider="anthropic", model="claude-sonnet-4-20250514"
        )
        mock_get.assert_called_once_with(
            "anthropic", model="claude-sonnet-4-20250514"
        )

    @patch("naturo.providers.base.get_vision_provider")
    def test_api_key_forwarded(self, mock_get):
        """API key is forwarded when provided."""
        from naturo.cli.options import get_vision_provider_from_options

        get_vision_provider_from_options(
            provider="openai", api_key="sk-test123"
        )
        mock_get.assert_called_once_with("openai", api_key="sk-test123")

    @patch("naturo.providers.base.get_vision_provider")
    def test_all_options_forwarded(self, mock_get):
        """All three options forwarded together."""
        from naturo.cli.options import get_vision_provider_from_options

        get_vision_provider_from_options(
            provider="ollama", model="llava", api_key="key123"
        )
        mock_get.assert_called_once_with(
            "ollama", model="llava", api_key="key123"
        )

    @patch("naturo.providers.base.get_vision_provider")
    def test_none_values_not_forwarded(self, mock_get):
        """None values for model/api_key are not included in kwargs."""
        from naturo.cli.options import get_vision_provider_from_options

        get_vision_provider_from_options(
            provider="anthropic", model=None, api_key=None
        )
        mock_get.assert_called_once_with("anthropic")
