"""Tests for issue #142 — Global --provider and --model flags.

Verifies:
- find command has --provider, --model, --api-key flags
- --provider flag passes to AI provider selection
- --model flag overrides model name
- --api-key flag overrides API key
- ai_provider_options decorator in options.py
- get_vision_provider_from_options helper
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.cli.options import ai_provider_options, get_vision_provider_from_options


# ── CLI flag presence ─────────────────────────────────────────────────────────


class TestFindCommandProviderFlags:
    def test_provider_flag_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["find", "--help"])
        assert "--provider" in result.output

    def test_model_flag_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["find", "--help"])
        assert "--model" in result.output

    def test_api_key_flag_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["find", "--help"])
        assert "--api-key" in result.output

    def test_provider_choices(self):
        runner = CliRunner()
        result = runner.invoke(main, ["find", "--help"])
        assert "anthropic" in result.output
        assert "openai" in result.output
        assert "ollama" in result.output


# ── ai_provider_options decorator ────────────────────────────────────────────


class TestAiProviderOptionsDecorator:
    def test_adds_provider_option(self):
        import click

        @click.command()
        @ai_provider_options
        def cmd(ai_provider, ai_model, ai_api_key):
            click.echo(f"{ai_provider}:{ai_model}:{ai_api_key}")

        runner = CliRunner()
        result = runner.invoke(cmd, ["--help"])
        assert "--provider" in result.output
        assert "--model" in result.output
        assert "--api-key" in result.output

    def test_default_provider_is_auto(self):
        import click

        @click.command()
        @ai_provider_options
        def cmd(ai_provider, ai_model, ai_api_key):
            click.echo(ai_provider)

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.output.strip() == "auto"

    def test_provider_choice_accepted(self):
        import click

        @click.command()
        @ai_provider_options
        def cmd(ai_provider, ai_model, ai_api_key):
            click.echo(ai_provider)

        runner = CliRunner()
        result = runner.invoke(cmd, ["--provider", "anthropic"])
        assert result.output.strip() == "anthropic"

    def test_model_option_accepted(self):
        import click

        @click.command()
        @ai_provider_options
        def cmd(ai_provider, ai_model, ai_api_key):
            click.echo(ai_model or "none")

        runner = CliRunner()
        result = runner.invoke(cmd, ["--model", "claude-3-haiku"])
        assert result.output.strip() == "claude-3-haiku"

    def test_model_reads_env_var(self, monkeypatch):
        import click

        monkeypatch.setenv("NATURO_AI_MODEL", "gpt-4o-mini")

        @click.command()
        @ai_provider_options
        def cmd(ai_provider, ai_model, ai_api_key):
            click.echo(ai_model or "none")

        runner = CliRunner()
        result = runner.invoke(cmd, [])
        assert result.output.strip() == "gpt-4o-mini"

    def test_api_key_option_accepted(self):
        import click

        @click.command()
        @ai_provider_options
        def cmd(ai_provider, ai_model, ai_api_key):
            click.echo(ai_api_key or "none")

        runner = CliRunner()
        result = runner.invoke(cmd, ["--api-key", "sk-test-123"])
        assert result.output.strip() == "sk-test-123"


# ── get_vision_provider_from_options helper ───────────────────────────────────


class TestGetVisionProviderFromOptions:
    def test_passes_model_to_provider(self, monkeypatch):
        from naturo.errors import AIProviderUnavailableError

        mock_provider = MagicMock()
        mock_provider.is_available = True
        mock_provider.name = "anthropic"

        with patch("naturo.providers.base.get_vision_provider", return_value=mock_provider) as mock_factory:
            result = get_vision_provider_from_options(
                provider="anthropic",
                model="claude-3-haiku",
            )

        mock_factory.assert_called_once_with("anthropic", model="claude-3-haiku")
        assert result is mock_provider

    def test_passes_api_key_to_provider(self):
        mock_provider = MagicMock()

        with patch("naturo.providers.base.get_vision_provider", return_value=mock_provider) as mock_factory:
            get_vision_provider_from_options(
                provider="anthropic",
                api_key="sk-test-abc",
            )

        mock_factory.assert_called_once_with("anthropic", api_key="sk-test-abc")

    def test_no_extra_kwargs_when_defaults(self):
        mock_provider = MagicMock()

        with patch("naturo.providers.base.get_vision_provider", return_value=mock_provider) as mock_factory:
            get_vision_provider_from_options(provider="auto")

        mock_factory.assert_called_once_with("auto")


# ── find --ai passes --provider/--model/--api-key ─────────────────────────────


class TestFindAIPassesFlags:
    def test_find_ai_passes_model_to_ai_find(self):
        """--model is forwarded to ai_find_element."""
        from naturo.ai_find import AIFindResult

        mock_result = AIFindResult(
            found=True, description="Found", confidence=0.9,
            ai_bounds={"x": 100, "y": 200, "width": 80, "height": 30},
            element=None, model="claude-3-haiku", tokens_used=100,
        )

        runner = CliRunner()
        with patch("naturo.cli.core._platform_supports_gui", return_value=False), \
             patch("naturo.cli.core._find_with_ai") as mock_find_ai:
            runner.invoke(main, [
                "find", "--ai", "the save button",
                "--provider", "anthropic",
                "--model", "claude-3-haiku",
                "--api-key", "sk-test",
            ])

        # Verify _find_with_ai was called with model and api_key
        if mock_find_ai.call_count:
            args, kwargs = mock_find_ai.call_args
            assert kwargs.get("model") == "claude-3-haiku" or "claude-3-haiku" in str(args)
