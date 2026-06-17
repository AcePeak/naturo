"""Tests for the global ``-j/--json`` contract on Click eager options (#874).

Click's ``--version`` / ``--help`` handlers and top-level usage errors (unknown
command/option) run before naturo's command code and emit plain text, breaking
``naturo -j --version`` / ``-j --help`` / ``-j <unknown-cmd>`` for scripts and
agents that pipe stdout into a JSON parser. The console-script wrapper
``naturo.cli.run`` closes that gap. These tests exercise the wrapper directly
(``click.testing.CliRunner`` invokes the group, bypassing the wrapper).
"""
from __future__ import annotations

import json

import pytest

from naturo.cli import _first_command_token, _wants_global_json, run
from naturo.version import __version__


def _run(monkeypatch, argv):
    """Invoke the console-script wrapper with a synthetic argv.

    Returns the ``SystemExit`` code raised by the wrapper.
    """
    monkeypatch.setattr("sys.argv", ["naturo", *argv])
    with pytest.raises(SystemExit) as excinfo:
        run()
    code = excinfo.value.code
    return 0 if code is None else code


# ── argv scanners ────────────────────────────────────────────────────────────

class TestGlobalJsonDetection:
    def test_detects_short_and_long_flag(self):
        assert _wants_global_json(["-j", "--version"]) is True
        assert _wants_global_json(["--json", "--help"]) is True

    def test_detects_flag_after_other_global_options(self):
        assert _wants_global_json(["--log-level", "debug", "-j", "--version"]) is True
        assert _wants_global_json(["-v", "--json", "list"]) is True

    def test_detects_combined_short_cluster(self):
        assert _wants_global_json(["-vj", "--version"]) is True

    def test_ignores_flag_after_subcommand(self):
        # -j after the command name is a subcommand-level flag, not global.
        assert _wants_global_json(["list", "-j"]) is False

    def test_absent(self):
        assert _wants_global_json(["--version"]) is False
        assert _wants_global_json(["list", "apps"]) is False


class TestFirstCommandToken:
    def test_none_for_global_only(self):
        assert _first_command_token(["-j", "--version"]) is None
        assert _first_command_token(["--json", "--help"]) is None

    def test_returns_subcommand(self):
        assert _first_command_token(["-j", "list", "apps"]) == "list"
        assert _first_command_token(["--log-level", "debug", "see"]) == "see"
        assert _first_command_token(["nonexistent-cmd"]) == "nonexistent-cmd"


# ── JSON contract on eager paths ─────────────────────────────────────────────

class TestJsonEagerOptions:
    def test_version_json(self, monkeypatch, capsys):
        code = _run(monkeypatch, ["-j", "--version"])
        data = json.loads(capsys.readouterr().out)
        assert code == 0
        assert data == {"success": True, "version": __version__}

    def test_help_json(self, monkeypatch, capsys):
        code = _run(monkeypatch, ["--json", "--help"])
        data = json.loads(capsys.readouterr().out)
        assert code == 0
        assert data["success"] is True
        help_obj = data["help"]
        assert "COMMAND" in help_obj["usage"]
        command_names = {c["name"] for c in help_obj["commands"]}
        assert {"see", "click", "type"} <= command_names
        option_names = " ".join(o["name"] for o in help_obj["options"])
        assert "--json" in option_names

    def test_unknown_command_json(self, monkeypatch, capsys):
        code = _run(monkeypatch, ["-j", "nonexistent-cmd"])
        data = json.loads(capsys.readouterr().out)
        assert code == 1  # runtime-error contract, not Click's UsageError exit 2
        assert data["success"] is False
        assert data["error"]["code"] == "UNKNOWN_COMMAND"
        assert "nonexistent-cmd" in data["error"]["message"]
        assert data["error"]["suggested_action"]


# ── regression: non-JSON behaviour unchanged ─────────────────────────────────

class TestPlainTextUnchanged:
    def test_version_plain_text(self, monkeypatch, capsys):
        code = _run(monkeypatch, ["--version"])
        out = capsys.readouterr().out
        assert code == 0
        assert "version" in out
        with pytest.raises(json.JSONDecodeError):
            json.loads(out.strip())

    def test_unknown_command_plain_text_exit_2(self, monkeypatch, capsys):
        code = _run(monkeypatch, ["nonexistent-cmd"])
        assert code == 2  # Click's UsageError exit code, unchanged
        assert "No such command" in capsys.readouterr().err
