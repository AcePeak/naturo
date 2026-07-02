"""Tests for the ``naturo doctor`` environment self-check (#898).

The command aggregates several diagnostics into one report. These tests pin the
JSON envelope shape, the exit-code contract (required checks gate exit), the
``--check-updates`` network gating, and the individual check helpers. Every test
is mock-based so it runs identically on Linux/macOS CI where no desktop session
or native DLL is available.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.cli import doctor_cmd
from naturo.cli.doctor_cmd import (
    Check,
    STATUS_FAIL,
    STATUS_OK,
    STATUS_WARN,
    _check_providers,
    _check_session,
    _check_version,
    _parse_version,
)
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
        Check("Optional dependency: pyvda", STATUS_WARN, "not installed", "pip install x"),
    ]


# ── _parse_version ────────────────────────────────────────────────────────────


class TestParseVersion:
    def test_simple(self):
        assert _parse_version("0.3.1") == (0, 3, 1)

    def test_trailing_suffix_reduced_to_int(self):
        assert _parse_version("1.2.3rc1") == (1, 2, 3)

    def test_ordering(self):
        assert _parse_version("0.4.0") > _parse_version("0.3.9")
        assert _parse_version("1.0") > _parse_version("0.9.9")

    def test_unparseable_is_empty(self):
        assert _parse_version("dev") == ()


# ── JSON envelope + exit-code contract ────────────────────────────────────────


class TestEnvelopeAndExit:
    def test_json_shape_success(self, runner: CliRunner):
        with patch.object(doctor_cmd, "_gather_checks", return_value=_ok_checks()):
            result = runner.invoke(main, ["doctor", "-j"])
        assert result.exit_code == 0
        import json

        payload = json.loads(result.output)
        assert payload["success"] is True
        assert payload["count"] == len(payload["checks"])
        for entry in payload["checks"]:
            assert set(entry) >= {"name", "status", "detail"}
            assert entry["status"] in {STATUS_OK, STATUS_WARN, STATUS_FAIL}

    def test_required_fail_exits_1_and_success_false(self, runner: CliRunner):
        checks = _ok_checks()
        checks[1] = Check(
            "Desktop session", STATUS_FAIL, "no session", "connect via RDP", required=True
        )
        with patch.object(doctor_cmd, "_gather_checks", return_value=checks):
            result = runner.invoke(main, ["doctor", "-j"])
        assert result.exit_code == 1
        import json

        assert json.loads(result.output)["success"] is False

    def test_warning_does_not_fail_exit(self, runner: CliRunner):
        checks = [
            Check("Desktop session", STATUS_OK, "interactive", required=True),
            Check("Native core", STATUS_OK, "loaded", required=True),
            Check("AI providers", STATUS_WARN, "no key", "set ANTHROPIC_API_KEY"),
        ]
        with patch.object(doctor_cmd, "_gather_checks", return_value=checks):
            result = runner.invoke(main, ["doctor", "-j"])
        assert result.exit_code == 0

    def test_suggested_action_omitted_when_absent(self, runner: CliRunner):
        with patch.object(doctor_cmd, "_gather_checks", return_value=_ok_checks()):
            result = runner.invoke(main, ["doctor", "-j"])
        import json

        version_entry = json.loads(result.output)["checks"][0]
        assert "suggested_action" not in version_entry


# ── Human output ──────────────────────────────────────────────────────────────


class TestHumanOutput:
    def test_headline_on_required_failure(self, runner: CliRunner):
        checks = _ok_checks()
        checks[1] = Check(
            "Desktop session", STATUS_FAIL, "no session", "connect via RDP", required=True
        )
        with patch.object(doctor_cmd, "_gather_checks", return_value=checks):
            result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 1
        assert "required check(s) failed" in result.output

    def test_all_passed_footer(self, runner: CliRunner):
        with patch.object(doctor_cmd, "_gather_checks", return_value=_ok_checks()):
            result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "All required checks passed." in result.output


# ── Version / update check (network gating) ───────────────────────────────────


class TestVersionCheck:
    def test_no_network_without_flag(self):
        with patch.object(doctor_cmd, "_fetch_latest_pypi_version") as fetch:
            check = _check_version(check_updates=False)
        fetch.assert_not_called()
        assert check.status == STATUS_OK
        assert __version__ in check.detail

    def test_stale_warns(self):
        with patch.object(doctor_cmd, "_fetch_latest_pypi_version", return_value="99.0.0"):
            check = _check_version(check_updates=True)
        assert check.status == STATUS_WARN
        assert check.suggested_action == "pip install --upgrade naturo"

    def test_up_to_date_ok(self):
        with patch.object(
            doctor_cmd, "_fetch_latest_pypi_version", return_value=__version__
        ):
            check = _check_version(check_updates=True)
        assert check.status == STATUS_OK
        assert "up to date" in check.detail

    def test_offline_warns(self):
        with patch.object(doctor_cmd, "_fetch_latest_pypi_version", return_value=None):
            check = _check_version(check_updates=True)
        assert check.status == STATUS_WARN


# ── Provider check ────────────────────────────────────────────────────────────


class TestProviderCheck:
    def test_env_key_makes_ok(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with patch("naturo.config.load_credentials", return_value={}):
            check = _check_providers()
        assert check.status == STATUS_OK
        assert "ANTHROPIC_API_KEY" in check.detail

    def test_none_configured_warns(self, monkeypatch):
        for key in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "OPENAI_API_KEY"):
            monkeypatch.delenv(key, raising=False)
        with patch("naturo.config.load_credentials", return_value={}):
            check = _check_providers()
        assert check.status == STATUS_WARN
        assert check.suggested_action is not None


# ── Session check (platform branches) ─────────────────────────────────────────


class TestSessionCheck:
    def test_non_windows_is_informational(self):
        with patch.object(doctor_cmd.sys, "platform", "linux"):
            check = _check_session()
        assert check.status == STATUS_WARN
        assert check.required is False

    def test_windows_non_interactive_is_required_fail(self):
        with patch.object(doctor_cmd.sys, "platform", "win32"), patch(
            "naturo.cli.interaction._common._is_current_session_interactive",
            return_value=False,
        ):
            check = _check_session()
        assert check.status == STATUS_FAIL
        assert check.required is True

    def test_windows_interactive_is_required_ok(self):
        with patch.object(doctor_cmd.sys, "platform", "win32"), patch(
            "naturo.cli.interaction._common._is_current_session_interactive",
            return_value=True,
        ):
            check = _check_session()
        assert check.status == STATUS_OK
        assert check.required is True
