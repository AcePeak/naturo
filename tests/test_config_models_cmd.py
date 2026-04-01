"""Tests for the 'naturo config models' CLI command."""
from __future__ import annotations

import json

from click.testing import CliRunner

from naturo.cli.config_cmd import config_cmd


class TestConfigModelsCommand:
    """Tests for 'naturo config models'."""

    def test_text_output_lists_providers(self) -> None:
        runner = CliRunner()
        result = runner.invoke(config_cmd, ["models"])
        assert result.exit_code == 0
        assert "anthropic" in result.output
        assert "openai" in result.output
        assert "google" in result.output
        assert "ollama" in result.output

    def test_text_output_lists_models(self) -> None:
        runner = CliRunner()
        result = runner.invoke(config_cmd, ["models"])
        assert result.exit_code == 0
        assert "claude-opus-4-6" in result.output
        assert "gpt-4o" in result.output
        assert "gemini-2.5-pro" in result.output
        assert "llava" in result.output

    def test_text_output_shows_aliases(self) -> None:
        runner = CliRunner()
        result = runner.invoke(config_cmd, ["models"])
        assert result.exit_code == 0
        assert "aliases:" in result.output

    def test_json_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(config_cmd, ["models", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "providers" in data
        assert "anthropic" in data["providers"]
        assert "openai" in data["providers"]
        assert "google" in data["providers"]
        assert "ollama" in data["providers"]

    def test_json_output_model_structure(self) -> None:
        runner = CliRunner()
        result = runner.invoke(config_cmd, ["models", "--json"])
        data = json.loads(result.output)
        for provider, info in data["providers"].items():
            assert "available" in info
            assert "models" in info
            assert isinstance(info["models"], list)
            for model in info["models"]:
                assert "id" in model
                assert "display" in model
                assert "aliases" in model

    def test_usage_hint_in_text_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(config_cmd, ["models"])
        assert result.exit_code == 0
        assert "--model" in result.output
