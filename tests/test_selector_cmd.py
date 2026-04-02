"""Tests for naturo selector CLI commands."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from naturo.cli import main
from naturo.cli import selector_cmd


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture()
def tmp_selectors(tmp_path):
    """Patch SELECTORS_DIR to temp directory."""
    with patch.object(selector_cmd, "SELECTORS_DIR", tmp_path):
        yield tmp_path


@pytest.fixture()
def tmp_builtin(tmp_path):
    """Create a temp builtin directory with sample data."""
    builtin_dir = tmp_path / "builtin"
    builtin_dir.mkdir()
    data = {
        "edit-area": {"selector": "app://notepad.exe/Edit[@name='Text Editor']", "description": "Main edit area"},
        "menu-file": {"selector": "app://notepad.exe/MenuItem[@name='File']", "description": "File menu"},
    }
    (builtin_dir / "notepad.json").write_text(json.dumps(data))
    with patch.object(selector_cmd, "BUILTIN_DIR", builtin_dir):
        yield builtin_dir


# ── selector save ────────────────────────────────────────────────────────────


class TestSelectorSave:
    def test_save_new_selector(self, runner, tmp_selectors):
        result = runner.invoke(main, [
            "selector", "save", "notepad", "save-btn",
            "app://notepad.exe/Button[@name='Save']",
        ])
        assert result.exit_code == 0
        assert "Saved" in result.output
        assert "@notepad/save-btn" in result.output
        # Verify file written
        data = json.loads((tmp_selectors / "notepad.json").read_text())
        assert "save-btn" in data
        assert data["save-btn"]["selector"] == "app://notepad.exe/Button[@name='Save']"

    def test_save_with_description(self, runner, tmp_selectors):
        result = runner.invoke(main, [
            "selector", "save", "notepad", "save-btn",
            "app://notepad.exe/Button[@name='Save']",
            "-d", "The save button in the toolbar",
        ])
        assert result.exit_code == 0
        data = json.loads((tmp_selectors / "notepad.json").read_text())
        assert data["save-btn"]["description"] == "The save button in the toolbar"

    def test_save_update_existing(self, runner, tmp_selectors):
        # Save initial
        runner.invoke(main, ["selector", "save", "notepad", "btn", "old-selector"])
        # Update
        result = runner.invoke(main, ["selector", "save", "notepad", "btn", "new-selector"])
        assert result.exit_code == 0
        assert "Updated" in result.output
        data = json.loads((tmp_selectors / "notepad.json").read_text())
        assert data["btn"]["selector"] == "new-selector"

    def test_save_json_output(self, runner, tmp_selectors):
        result = runner.invoke(main, [
            "selector", "save", "notepad", "btn", "sel", "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["name"] == "btn"


# ── selector list ────────────────────────────────────────────────────────────


class TestSelectorList:
    def test_list_empty(self, runner, tmp_selectors):
        result = runner.invoke(main, ["selector", "list"])
        assert result.exit_code == 0
        assert "No saved selectors" in result.output

    def test_list_with_selectors(self, runner, tmp_selectors):
        # Save some selectors
        runner.invoke(main, ["selector", "save", "notepad", "btn1", "sel1"])
        runner.invoke(main, ["selector", "save", "chrome", "addr", "sel2"])
        result = runner.invoke(main, ["selector", "list"])
        assert result.exit_code == 0
        assert "notepad" in result.output
        assert "chrome" in result.output

    def test_list_filter_by_app(self, runner, tmp_selectors):
        runner.invoke(main, ["selector", "save", "notepad", "btn1", "sel1"])
        runner.invoke(main, ["selector", "save", "chrome", "addr", "sel2"])
        result = runner.invoke(main, ["selector", "list", "--app", "notepad"])
        assert result.exit_code == 0
        assert "notepad" in result.output
        assert "chrome" not in result.output

    def test_list_builtin(self, runner, tmp_selectors, tmp_builtin):
        result = runner.invoke(main, ["selector", "list", "--builtin"])
        assert result.exit_code == 0
        assert "notepad" in result.output
        assert "edit-area" in result.output

    def test_list_json(self, runner, tmp_selectors):
        runner.invoke(main, ["selector", "save", "notepad", "btn1", "sel1"])
        result = runner.invoke(main, ["selector", "list", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "notepad" in data


# ── selector show ────────────────────────────────────────────────────────────


class TestSelectorShow:
    def test_show_app_selectors(self, runner, tmp_selectors):
        runner.invoke(main, ["selector", "save", "notepad", "btn1", "sel1"])
        runner.invoke(main, ["selector", "save", "notepad", "btn2", "sel2"])
        result = runner.invoke(main, ["selector", "show", "notepad"])
        assert result.exit_code == 0
        assert "btn1" in result.output
        assert "btn2" in result.output

    def test_show_empty(self, runner, tmp_selectors):
        result = runner.invoke(main, ["selector", "show", "nothing"])
        assert result.exit_code == 0
        assert "No selectors" in result.output


# ── selector delete ──────────────────────────────────────────────────────────


class TestSelectorDelete:
    def test_delete_selector(self, runner, tmp_selectors):
        runner.invoke(main, ["selector", "save", "notepad", "btn1", "sel1"])
        result = runner.invoke(main, ["selector", "delete", "notepad", "btn1", "--force"])
        assert result.exit_code == 0
        assert "Deleted" in result.output
        # File should be removed when empty
        assert not (tmp_selectors / "notepad.json").exists()

    def test_delete_keeps_other_selectors(self, runner, tmp_selectors):
        runner.invoke(main, ["selector", "save", "notepad", "btn1", "sel1"])
        runner.invoke(main, ["selector", "save", "notepad", "btn2", "sel2"])
        result = runner.invoke(main, ["selector", "delete", "notepad", "btn1", "--force"])
        assert result.exit_code == 0
        data = json.loads((tmp_selectors / "notepad.json").read_text())
        assert "btn1" not in data
        assert "btn2" in data

    def test_delete_not_found(self, runner, tmp_selectors):
        result = runner.invoke(main, ["selector", "delete", "notepad", "nope", "--force"])
        assert result.exit_code != 0


# ── selector clear ───────────────────────────────────────────────────────────


class TestSelectorClear:
    def test_clear_app(self, runner, tmp_selectors):
        runner.invoke(main, ["selector", "save", "notepad", "btn1", "sel1"])
        runner.invoke(main, ["selector", "save", "notepad", "btn2", "sel2"])
        result = runner.invoke(main, ["selector", "clear", "notepad", "--force"])
        assert result.exit_code == 0
        assert "Cleared 2" in result.output
        assert not (tmp_selectors / "notepad.json").exists()


# ── selector export ──────────────────────────────────────────────────────────


class TestSelectorExport:
    def test_export_to_stdout(self, runner, tmp_selectors):
        runner.invoke(main, ["selector", "save", "notepad", "btn1", "sel1"])
        result = runner.invoke(main, ["selector", "export", "notepad"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["app"] == "notepad"
        assert "btn1" in data["selectors"]

    def test_export_to_file(self, runner, tmp_selectors, tmp_path):
        runner.invoke(main, ["selector", "save", "notepad", "btn1", "sel1"])
        out = str(tmp_path / "export.json")
        result = runner.invoke(main, ["selector", "export", "notepad", "-o", out])
        assert result.exit_code == 0
        assert Path(out).exists()
        data = json.loads(Path(out).read_text())
        assert data["app"] == "notepad"


# ── selector import ──────────────────────────────────────────────────────────


class TestSelectorImport:
    def test_import_merge(self, runner, tmp_selectors, tmp_path):
        # Existing selector
        runner.invoke(main, ["selector", "save", "notepad", "existing", "old-sel"])
        # Import file
        import_file = tmp_path / "import.json"
        import_file.write_text(json.dumps({
            "app": "notepad",
            "selectors": {"imported": {"selector": "new-sel", "description": ""}},
        }))
        result = runner.invoke(main, ["selector", "import", str(import_file)])
        assert result.exit_code == 0
        assert "merged" in result.output
        data = json.loads((tmp_selectors / "notepad.json").read_text())
        assert "existing" in data  # kept
        assert "imported" in data  # added

    def test_import_replace(self, runner, tmp_selectors, tmp_path):
        runner.invoke(main, ["selector", "save", "notepad", "existing", "old-sel"])
        import_file = tmp_path / "import.json"
        import_file.write_text(json.dumps({
            "app": "notepad",
            "selectors": {"imported": {"selector": "new-sel", "description": ""}},
        }))
        result = runner.invoke(main, ["selector", "import", str(import_file), "--replace"])
        assert result.exit_code == 0
        assert "replaced" in result.output
        data = json.loads((tmp_selectors / "notepad.json").read_text())
        assert "existing" not in data  # replaced
        assert "imported" in data


# ── selector test ────────────────────────────────────────────────────────────


class TestSelectorTest:
    def test_test_valid_selector(self, runner, tmp_selectors):
        runner.invoke(main, [
            "selector", "save", "notepad", "edit",
            "app://notepad.exe/Edit[@name='Text Editor']",
        ])
        result = runner.invoke(main, ["selector", "test", "notepad", "edit"])
        assert result.exit_code == 0
        assert "Parsed: OK" in result.output

    def test_test_not_found(self, runner, tmp_selectors):
        result = runner.invoke(main, ["selector", "test", "notepad", "nope"])
        assert result.exit_code != 0

    def test_test_json_output(self, runner, tmp_selectors):
        runner.invoke(main, [
            "selector", "save", "notepad", "edit",
            "app://notepad.exe/Edit[@name='Text Editor']",
        ])
        result = runner.invoke(main, ["selector", "test", "notepad", "edit", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["parsed"] is True


# ── help ─────────────────────────────────────────────────────────────────────


class TestSelectorHelp:
    def test_selector_help(self, runner):
        result = runner.invoke(main, ["selector", "--help"])
        assert result.exit_code == 0
        assert "save" in result.output
        assert "list" in result.output
        assert "export" in result.output
        assert "import" in result.output
        assert "test" in result.output

    def test_selector_save_help(self, runner):
        result = runner.invoke(main, ["selector", "save", "--help"])
        assert result.exit_code == 0

    def test_selector_import_help(self, runner):
        result = runner.invoke(main, ["selector", "import", "--help"])
        assert result.exit_code == 0
