"""Tests for the global ``-j/--json`` contract on subcommand usage errors (#872).

Click raises a ``UsageError`` for every parse-time failure — unknown option,
missing required argument, too-many-arguments, and invalid option/argument
values (bad int/float/choice). For *subcommands* these errors were printed as a
plain Click banner on stderr with exit code 2, even when ``-j``/``--json`` was
requested, so scripts piping ``naturo <cmd> ... -j`` into a JSON parser crashed.

The top-level twin of this bug was fixed by #874; this closes the gap for every
subcommand. The console-script wrapper ``naturo.cli.run`` now wraps *all*
parse-time ``UsageError``\\s in the standard JSON envelope (exit 1) whenever a
JSON flag appears anywhere on the command line.

These tests exercise the wrapper directly because ``click.testing.CliRunner``
invokes the group and bypasses the wrapper. They are pure CLI level — no DLL,
no desktop session, no input injection (every case fails during argument
parsing, before any command body runs).
"""
from __future__ import annotations

import json

import pytest

from naturo.cli import _wants_json, run


def _run(monkeypatch, argv):
    """Invoke the console-script wrapper with a synthetic argv.

    Returns a ``(exit_code, stdout, stderr)`` tuple.
    """
    monkeypatch.setattr("sys.argv", ["naturo", *argv])
    with pytest.raises(SystemExit) as excinfo:
        run()
    code = excinfo.value.code
    return 0 if code is None else code


# ── argv scanner ─────────────────────────────────────────────────────────────

class TestWantsJson:
    def test_detects_flag_anywhere(self):
        assert _wants_json(["-j", "see"]) is True
        assert _wants_json(["see", "--depth", "abc", "-j"]) is True
        assert _wants_json(["--json", "list"]) is True

    def test_detects_combined_short_cluster(self):
        assert _wants_json(["-vj", "see"]) is True
        assert _wants_json(["see", "-vj"]) is True

    def test_skips_global_value_option_value(self):
        # The value of --log-level must not be mistaken for a flag.
        assert _wants_json(["--log-level", "debug", "see"]) is False

    def test_stops_at_double_dash(self):
        # Everything after ``--`` is positional, never a JSON flag.
        assert _wants_json(["type", "--", "-j"]) is False

    def test_absent(self):
        assert _wants_json(["see", "apps"]) is False
        assert _wants_json(["list"]) is False


# ── JSON envelope on every parse-time error category (R135) ──────────────────

class TestSubcommandUsageErrorJson:
    def _assert_envelope(self, monkeypatch, capsys, argv, expected_code):
        code = _run(monkeypatch, argv)
        out = capsys.readouterr().out
        data = json.loads(out)  # must be a single, parseable JSON document
        assert code == 1, f"{argv!r} should exit 1, got {code}"
        assert data["success"] is False
        assert data["error"]["code"] == expected_code
        assert data["error"]["message"]
        assert data["error"]["suggested_action"]
        return data

    def test_missing_required_argument(self, monkeypatch, capsys):
        # ``app find`` requires a positional NAME and defines ``-j``, so omitting
        # the argument is a parse-time "Missing argument" error. (``clipboard
        # set`` used to be the exemplar here but gained optional --file/stdin
        # sources in #888, so its TEXT argument is no longer required.)
        data = self._assert_envelope(
            monkeypatch, capsys, ["app", "find", "-j"], "INVALID_INPUT"
        )
        assert "Missing argument" in data["error"]["message"]

    def test_unknown_flag(self, monkeypatch, capsys):
        data = self._assert_envelope(
            monkeypatch, capsys, ["type", "--bogus-flag-xyz", "-j"], "UNKNOWN_OPTION"
        )
        assert "bogus-flag-xyz" in data["error"]["message"]

    def test_too_many_positional_args(self, monkeypatch, capsys):
        self._assert_envelope(
            monkeypatch, capsys, ["wait", "1", "2", "-j"], "INVALID_INPUT"
        )

    def test_invalid_float_value(self, monkeypatch, capsys):
        self._assert_envelope(
            monkeypatch, capsys, ["wait", "abc", "-j"], "INVALID_INPUT"
        )

    def test_invalid_int_value(self, monkeypatch, capsys):
        self._assert_envelope(
            monkeypatch, capsys, ["see", "--hwnd", "abc", "-j"], "INVALID_INPUT"
        )

    def test_invalid_root_choice_value(self, monkeypatch, capsys):
        # Root-level option error (bad --log-level choice) with -j after the
        # subcommand still gets the envelope (category 6).
        self._assert_envelope(
            monkeypatch, capsys, ["--log-level", "bogus", "see", "-j"], "INVALID_INPUT"
        )

    def test_unknown_subgroup_command(self, monkeypatch, capsys):
        data = self._assert_envelope(
            monkeypatch, capsys, ["app", "bogus-subcmd", "-j"], "UNKNOWN_COMMAND"
        )
        assert "bogus-subcmd" in data["error"]["message"]


class TestFlagPositionVariants:
    """``-j`` works before or after the subcommand (issue body)."""

    def _envelope_code(self, monkeypatch, capsys, argv):
        code = _run(monkeypatch, argv)
        data = json.loads(capsys.readouterr().out)
        assert code == 1
        assert data["success"] is False
        return data["error"]["code"]

    def test_global_flag_before_subcommand(self, monkeypatch, capsys):
        assert self._envelope_code(
            monkeypatch, capsys, ["-j", "see", "--hwnd", "abc"]
        ) == "INVALID_INPUT"

    def test_long_global_flag_before_subcommand(self, monkeypatch, capsys):
        assert self._envelope_code(
            monkeypatch, capsys, ["--json", "see", "--hwnd", "abc"]
        ) == "INVALID_INPUT"

    def test_flag_after_subcommand(self, monkeypatch, capsys):
        assert self._envelope_code(
            monkeypatch, capsys, ["see", "--hwnd", "abc", "-j"]
        ) == "INVALID_INPUT"


# ── regression: non-JSON behaviour is byte-for-byte Click ────────────────────

class TestPlainTextUnchanged:
    def test_missing_arg_plain_text_exit_2(self, monkeypatch, capsys):
        # See test_missing_required_argument: ``app find`` is the missing-arg
        # exemplar now that ``clipboard set`` accepts --file/stdin (#888).
        code = _run(monkeypatch, ["app", "find"])
        captured = capsys.readouterr()
        assert code == 2  # Click's UsageError exit code, unchanged
        assert "Usage: naturo app find" in captured.err
        assert captured.out == ""  # nothing on stdout — no stray JSON

    def test_invalid_value_plain_text_exit_2(self, monkeypatch, capsys):
        code = _run(monkeypatch, ["see", "--hwnd", "abc"])
        captured = capsys.readouterr()
        assert code == 2
        assert "Usage: naturo see" in captured.err
        assert captured.out == ""
