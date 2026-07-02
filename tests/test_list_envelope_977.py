"""Tests for #977: ``visual list -j`` and ``selector show -j`` envelope contract.

Follow-up to #876 (which normalized ``selector list -j`` / ``record list -j``).
These two remaining read commands still drifted from the standard
``{success, <collection>, count}`` JSON envelope:

* ``visual list -j``     -> bare ``{"baselines": [...]}`` (no ``success``/``count``)
* ``selector show <app> -j`` -> bare ``{"user": {...}, "builtin": {...}}``
  (no ``success``; a nonexistent app was indistinguishable from an existing app
  with zero selectors)

These tests pin the corrected envelopes. They are pure CLI/JSON tests with no
DLL, desktop session, or input simulation required.
"""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.cli import selector_cmd


@pytest.fixture
def runner():
    return CliRunner()


# ── visual list -j ───────────────────────────────────────────────────────────


class TestVisualListEnvelope:
    def test_empty_has_success_and_count(self, runner, tmp_path, monkeypatch):
        """Empty baseline set still emits the standard success envelope."""
        monkeypatch.setattr(
            "naturo.cli.visual_cmd.list_baselines", lambda: []
        )
        result = runner.invoke(main, ["visual", "list", "-j"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["baselines"] == []
        assert data["count"] == 0

    def test_populated_has_success_and_count(self, runner, monkeypatch):
        """Populated baseline set reports success, the list, and its count."""
        fake = [
            {"name": "home", "size": [800, 600], "created_at": "2026-06-17T00:00:00"},
            {"name": "login", "size": [800, 600], "created_at": "2026-06-17T00:00:01"},
        ]
        monkeypatch.setattr(
            "naturo.cli.visual_cmd.list_baselines", lambda: fake
        )
        result = runner.invoke(main, ["visual", "list", "-j"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["baselines"] == fake
        assert data["count"] == 2


# ── selector show <app> -j ───────────────────────────────────────────────────


class TestSelectorShowEnvelope:
    @pytest.fixture(autouse=True)
    def tmp_selectors(self, tmp_path):
        """Redirect user-selector storage to a temp dir for isolation."""
        with patch.object(selector_cmd, "SELECTORS_DIR", tmp_path):
            yield tmp_path

    def test_existing_app_has_success_app_count(self, runner):
        runner.invoke(main, ["selector", "save", "notepad", "btn1", "@notepad/x"])
        runner.invoke(main, ["selector", "save", "notepad", "btn2", "@notepad/y"])
        result = runner.invoke(main, ["selector", "show", "notepad", "-j"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["app"] == "notepad"
        assert set(data["selectors"]) == {"btn1", "btn2"}
        assert "builtin" in data
        assert data["count"] == len(data["selectors"]) + len(data["builtin"])

    def test_nonexistent_app_is_loud_failure(self, runner):
        """A nonexistent app (no user and no built-in selectors) must fail loudly,
        not return an empty-but-successful envelope."""
        result = runner.invoke(
            main, ["selector", "show", "nonexistentABCXYZ", "-j"]
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["success"] is False
        # error is the canonical object envelope (#993), not a bare string.
        assert data["error"]["code"] == "SELECTOR_NOT_FOUND"
        assert "nonexistentABCXYZ" in data["error"]["message"]

    def test_text_mode_empty_unchanged(self, runner):
        """Text mode for a nonexistent app stays a friendly exit-0 message
        (no behavioural regression for humans)."""
        result = runner.invoke(main, ["selector", "show", "nonexistentABCXYZ"])
        assert result.exit_code == 0
        assert "No selectors" in result.output
