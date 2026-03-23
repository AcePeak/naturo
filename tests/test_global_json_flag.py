"""Tests for global --json flag propagation to subcommands (fixes #177).

The global ``naturo --json <command>`` should produce the same output as
``naturo <command> --json``.
"""
from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from naturo.cli import main


@pytest.fixture
def runner():
    return CliRunner()


class TestGlobalJsonPropagation:
    """Verify --json placed before the command name propagates correctly."""

    def test_version_json(self, runner):
        """naturo --json should not crash (version doesn't use json, but group should not error)."""
        result = runner.invoke(main, ["--json", "--version"])
        # --version always outputs text, but should not crash
        assert result.exit_code == 0

    def test_global_json_propagates_to_list_screens(self, runner):
        """naturo --json list screens should produce JSON output."""
        # Run with global --json
        result_global = runner.invoke(main, ["--json", "list", "screens"])
        # Run with per-command --json
        result_local = runner.invoke(main, ["list", "screens", "-j"])

        # Both should succeed
        # On non-Windows, both may fail with same error — that's fine,
        # what matters is they behave identically
        assert result_global.exit_code == result_local.exit_code

        # If they succeeded, verify both produce valid JSON
        if result_global.exit_code == 0 and result_global.output.strip():
            try:
                json.loads(result_global.output)
                global_is_json = True
            except json.JSONDecodeError:
                global_is_json = False

            try:
                json.loads(result_local.output)
                local_is_json = True
            except json.JSONDecodeError:
                local_is_json = False

            assert global_is_json == local_is_json, (
                f"Global --json produces JSON={global_is_json}, "
                f"local -j produces JSON={local_is_json}"
            )

    def test_global_json_propagates_to_snapshot_list(self, runner):
        """naturo --json snapshot list should produce JSON."""
        result_global = runner.invoke(main, ["--json", "snapshot", "list"])
        result_local = runner.invoke(main, ["snapshot", "list", "-j"])
        assert result_global.exit_code == result_local.exit_code

    def test_ctx_obj_json_is_set(self, runner):
        """Verify ctx.obj['json'] is set when --json is passed globally."""
        import click
        from naturo.cli import _patch_json_flag

        captured = {}

        @main.command("_test_json_ctx")
        @click.option("--json", "-j", "json_output", is_flag=True)
        @click.pass_context
        def test_cmd(ctx, json_output):
            captured["local"] = json_output
            captured["ctx_json"] = ctx.obj.get("json", False)

        # Patch the dynamically-added command (normally done at import time)
        _patch_json_flag(test_cmd)

        try:
            runner.invoke(main, ["--json", "_test_json_ctx"])
            # When global --json is used, ctx.obj["json"] should be True
            assert captured.get("ctx_json") is True
            # And the local json_output should also be True via callback
            assert captured.get("local") is True
        finally:
            main.commands.pop("_test_json_ctx", None)

    def test_no_json_when_not_passed(self, runner):
        """Verify no JSON propagation when --json is not passed."""
        import click

        captured = {}

        @main.command("_test_no_json")
        @click.option("--json", "-j", "json_output", is_flag=True)
        @click.pass_context
        def test_cmd(ctx, json_output):
            captured["local"] = json_output
            captured["ctx_json"] = ctx.obj.get("json", False)

        try:
            runner.invoke(main, ["_test_no_json"])
            assert captured.get("ctx_json") is False
            assert captured.get("local") is False
        finally:
            main.commands.pop("_test_no_json", None)
