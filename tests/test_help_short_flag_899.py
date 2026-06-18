"""Tests for ``-h`` as a POSIX synonym of ``--help`` (#899).

``-h`` is the de-facto Unix shorthand for ``--help`` (git, curl, pip, python, …).
naturo previously accepted only ``--help`` and rejected ``-h`` with
``Error: No such option: -h`` and exit code 2 — treating an idiomatic
invocation as a usage error. These tests pin the fix: ``-h`` must behave
identically to ``--help`` at the root group, on every subcommand, and on nested
subgroup commands, and the global ``-j`` JSON-help contract must stay consistent
between ``-h`` and ``--help``.
"""
from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from naturo.cli import main, run


# Representative slice of the command surface: root, plain subcommands, a
# subgroup, and a nested subgroup command — covering the inheritance paths.
_HELP_TARGETS = [
    [],                  # root group
    ["see"],
    ["click"],
    ["type"],
    ["press"],
    ["find"],
    ["wait"],
    ["get"],
    ["set"],
    ["app"],             # subgroup itself
    ["app", "launch"],   # nested subgroup command
    ["clipboard", "set"],
]


class TestShortHelpFlag:
    """``-h`` is accepted everywhere ``--help`` is."""

    @pytest.mark.parametrize("argv", _HELP_TARGETS)
    def test_short_flag_matches_long_flag(self, argv):
        """``<cmd> -h`` exits 0 with the same output as ``<cmd> --help``."""
        runner = CliRunner()
        short = runner.invoke(main, [*argv, "-h"])
        long = runner.invoke(main, [*argv, "--help"])
        assert short.exit_code == 0, f"{argv} -h exited {short.exit_code}: {short.output}"
        assert long.exit_code == 0
        assert short.output == long.output
        assert "Usage:" in short.output
        assert "No such option" not in short.output

    def test_root_short_flag_lists_commands(self):
        """``naturo -h`` shows the command list, like ``--help``."""
        runner = CliRunner()
        result = runner.invoke(main, ["-h"])
        assert result.exit_code == 0
        assert "see" in result.output
        assert "click" in result.output

    def test_help_record_advertises_short_flag(self):
        """The rendered help text advertises ``-h`` alongside ``--help``."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "-h, --help" in result.output

    @pytest.mark.parametrize("argv", [["click"], ["type"], ["app", "launch"]])
    def test_short_flag_survives_standalone_help_caching(self, argv):
        """``-h`` works even after a command is first invoked parentless.

        Click (>=8.1.8) caches the help option on first use, derived from the
        first context the command runs under. A parentless invocation — e.g.
        ``CliRunner().invoke(subcommand, ["--help"])`` elsewhere in the suite —
        defaults to ``["--help"]`` and would cache a help option without ``-h``,
        making a later ``<cmd> -h`` fail with exit 2. This pins that the
        per-command ``help_option_names`` stamping defeats that order-dependence
        (regression for the CI-only failure on click 8.4.1; see #899).
        """
        runner = CliRunner()
        # Resolve and pollute the leaf command standalone (parentless context).
        leaf = main
        for token in argv:
            leaf = leaf.commands[token]
        runner.invoke(leaf, ["--help"])
        # ``-h`` through the root must still be accepted.
        result = runner.invoke(main, [*argv, "-h"])
        assert result.exit_code == 0, f"{argv} -h exited {result.exit_code}: {result.output}"
        assert "No such option" not in result.output


class TestShortHelpJsonContract:
    """The global ``-j`` JSON-help envelope is identical for ``-h`` and ``--help``."""

    def _run_json(self, monkeypatch, capsys, argv):
        monkeypatch.setattr("sys.argv", ["naturo", *argv])
        with pytest.raises(SystemExit) as excinfo:
            run()
        code = excinfo.value.code
        out = capsys.readouterr().out
        return (0 if code is None else code), out

    def test_json_short_help_matches_long_help(self, monkeypatch, capsys):
        """``naturo -j -h`` emits the same JSON envelope as ``naturo -j --help``."""
        code_short, out_short = self._run_json(monkeypatch, capsys, ["-j", "-h"])
        code_long, out_long = self._run_json(monkeypatch, capsys, ["-j", "--help"])
        assert code_short == 0
        assert code_long == 0
        data_short = json.loads(out_short)
        data_long = json.loads(out_long)
        assert data_short["success"] is True
        assert data_short == data_long
