"""Tests for built-in selector templates (issue #104).

Validates that all 20 built-in app selector templates are correctly
formatted, loadable, and integrate with the selector CLI commands.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.cli import selector_cmd

BUILTIN_DIR = Path(__file__).parent.parent / "naturo" / "selectors_builtin"

EXPECTED_APPS = [
    "calc",
    "chrome",
    "cmd",
    "code",
    "control",
    "excel",
    "explorer",
    "firefox",
    "msedge",
    "mspaint",
    "notepad",
    "outlook",
    "powerpnt",
    "regedit",
    "snippingtool",
    "systemsettings",
    "taskmgr",
    "teams",
    "windowsterminal",
    "winword",
]


@pytest.fixture()
def runner():
    return CliRunner()


class TestBuiltinTemplateFiles:
    """Validate the template JSON files on disk."""

    def test_builtin_directory_exists(self):
        assert BUILTIN_DIR.is_dir(), f"Missing directory: {BUILTIN_DIR}"

    def test_all_20_apps_present(self):
        found = sorted(f.stem for f in BUILTIN_DIR.glob("*.json"))
        assert found == EXPECTED_APPS

    @pytest.mark.parametrize("app", EXPECTED_APPS)
    def test_valid_json(self, app):
        path = BUILTIN_DIR / f"{app}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert len(data) >= 1, f"{app}.json must have at least 1 selector"

    @pytest.mark.parametrize("app", EXPECTED_APPS)
    def test_selector_format(self, app):
        path = BUILTIN_DIR / f"{app}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for name, info in data.items():
            assert isinstance(info, dict), f"{app}/{name}: value must be dict"
            assert "selector" in info, f"{app}/{name}: missing 'selector' key"
            assert "description" in info, f"{app}/{name}: missing 'description' key"
            assert info["selector"].startswith("app://"), (
                f"{app}/{name}: selector must start with app://"
            )
            assert len(info["description"]) > 0, (
                f"{app}/{name}: description must not be empty"
            )

    @pytest.mark.parametrize("app", EXPECTED_APPS)
    def test_selector_names_are_kebab_case(self, app):
        path = BUILTIN_DIR / f"{app}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for name in data:
            assert name == name.lower(), f"{app}/{name}: must be lowercase"
            assert " " not in name, f"{app}/{name}: no spaces allowed"

    def test_total_selector_count(self):
        total = 0
        for f in BUILTIN_DIR.glob("*.json"):
            data = json.loads(f.read_text(encoding="utf-8"))
            total += len(data)
        assert total >= 100, f"Expected 100+ selectors, got {total}"


class TestBuiltinCLIIntegration:
    """Test that built-in selectors load through the CLI commands."""

    def test_list_builtin_loads_all_apps(self, runner):
        result = runner.invoke(main, ["selector", "list", "--builtin"])
        assert result.exit_code == 0
        for app in EXPECTED_APPS:
            assert app in result.output, f"Missing app '{app}' in list output"

    def test_list_builtin_json(self, runner):
        result = runner.invoke(main, ["selector", "list", "--builtin", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        # #876: standard envelope — success + count + a flat selector list,
        # each record self-describing its owning app.
        assert data["success"] is True
        assert data["count"] == len(data["selectors"])
        apps = {entry["app"] for entry in data["selectors"]}
        assert len(apps) == 20
        for app in EXPECTED_APPS:
            assert app in apps

    def test_list_builtin_filter_by_app(self, runner):
        result = runner.invoke(main, [
            "selector", "list", "--builtin", "--app", "notepad",
        ])
        assert result.exit_code == 0
        assert "notepad" in result.output
        assert "edit-area" in result.output

    def test_show_merges_builtin(self, runner):
        result = runner.invoke(main, ["selector", "show", "calc"])
        assert result.exit_code == 0
        assert "display" in result.output
        assert "CalculatorResults" in result.output

    def test_list_builtin_nonexistent_app(self, runner):
        result = runner.invoke(main, [
            "selector", "list", "--builtin", "--app", "nonexistent",
        ])
        assert result.exit_code == 0
        assert "No built-in selectors" in result.output


class TestPackageData:
    """Ensure built-in templates are included in package distribution."""

    def test_pyproject_includes_json_templates(self):
        # ``tomllib`` is stdlib only on Python 3.11+; fall back to the ``tomli``
        # backport (declared as a dev dependency) on 3.9/3.10 (#910).
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        with open(pyproject, "rb") as f:
            config = tomllib.load(f)
        package_data = config["tool"]["setuptools"]["package-data"]["naturo"]
        assert "selectors_builtin/*.json" in package_data


class TestBuiltinLoaderFunction:
    """Test the _list_builtin_selectors function directly."""

    def test_loads_all_apps(self):
        result = selector_cmd._list_builtin_selectors()
        assert len(result) == 20
        for app in EXPECTED_APPS:
            assert app in result

    def test_each_app_has_selectors(self):
        result = selector_cmd._list_builtin_selectors()
        for app, selectors in result.items():
            assert len(selectors) >= 1, f"{app} must have at least 1 selector"
            for name, info in selectors.items():
                assert "selector" in info
                assert "description" in info
