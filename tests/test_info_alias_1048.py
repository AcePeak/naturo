"""Tests for ``naturo info`` as an alias of ``naturo doctor`` (#1048).

The ``doctor`` proposal (#898) advertised ``naturo info`` as an alias, but the
command was never wired — ``naturo info`` exited 2 with "no such command". These
tests pin the alias contract: ``info`` produces the same envelope, exit code, and
flag behaviour as ``doctor``, and stays hidden from the top-level help so
``doctor`` remains the single advertised name. Every test is mock-based so it
runs identically on Linux/macOS CI where no desktop session or native DLL exists.
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.cli import doctor_cmd
from naturo.cli.doctor_cmd import Check, STATUS_FAIL, STATUS_OK, STATUS_WARN
from naturo.version import __version__


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _ok_checks() -> list[Check]:
    """A minimal all-passing check set (both required checks ok)."""
    return [
        Check("naturo version", STATUS_OK, __version__),
        Check("Desktop session", STATUS_OK, "interactive", required=True),
        Check("Native core (naturo_core.dll)", STATUS_OK, "loaded", required=True),
        Check("AI providers", STATUS_WARN, "no key", "set ANTHROPIC_API_KEY"),
    ]


class TestInfoAlias:
    def test_info_command_is_registered(self):
        assert "info" in main.commands

    def test_info_hidden_doctor_visible(self):
        """`info` must not clutter the top-level help; `doctor` stays advertised."""
        assert main.commands["info"].hidden is True
        assert main.commands["doctor"].hidden is False

    def test_info_json_matches_doctor_json(self, runner: CliRunner):
        with patch.object(doctor_cmd, "_gather_checks", return_value=_ok_checks()):
            doctor_result = runner.invoke(main, ["doctor", "-j"])
            info_result = runner.invoke(main, ["info", "-j"])
        assert doctor_result.exit_code == 0
        assert info_result.exit_code == doctor_result.exit_code
        assert json.loads(info_result.output) == json.loads(doctor_result.output)

    def test_info_human_matches_doctor_human(self, runner: CliRunner):
        with patch.object(doctor_cmd, "_gather_checks", return_value=_ok_checks()):
            doctor_result = runner.invoke(main, ["doctor"])
            info_result = runner.invoke(main, ["info"])
        assert info_result.output == doctor_result.output
        assert info_result.exit_code == doctor_result.exit_code == 0

    def test_info_propagates_failure_exit_code(self, runner: CliRunner):
        checks = _ok_checks()
        checks[1] = Check(
            "Desktop session", STATUS_FAIL, "no session", "connect via RDP", required=True
        )
        with patch.object(doctor_cmd, "_gather_checks", return_value=checks):
            result = runner.invoke(main, ["info", "-j"])
        assert result.exit_code == 1
        assert json.loads(result.output)["success"] is False

    def test_info_forwards_check_updates_flag(self, runner: CliRunner):
        """`--check-updates` must reach `_gather_checks` through the alias too."""
        seen: dict[str, bool] = {}

        def _fake_gather(check_updates: bool) -> list[Check]:
            seen["check_updates"] = check_updates
            return _ok_checks()

        with patch.object(doctor_cmd, "_gather_checks", _fake_gather):
            runner.invoke(main, ["info", "--check-updates", "-j"])
        assert seen["check_updates"] is True
