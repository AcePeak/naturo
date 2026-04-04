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


# ── selector load ────────────────────────────────────────────────────────────


class TestSelectorLoad:
    def test_load_user_selector(self, runner, tmp_selectors):
        runner.invoke(main, [
            "selector", "save", "notepad", "save-btn",
            "app://notepad.exe/Button[@name='Save']",
            "-d", "Save button",
        ])
        result = runner.invoke(main, ["selector", "load", "notepad", "save-btn"])
        assert result.exit_code == 0
        assert "app://notepad.exe/Button[@name='Save']" in result.output

    def test_load_not_found(self, runner, tmp_selectors):
        result = runner.invoke(main, ["selector", "load", "notepad", "nope"])
        assert result.exit_code != 0

    def test_load_json_output(self, runner, tmp_selectors):
        runner.invoke(main, [
            "selector", "save", "notepad", "save-btn",
            "app://notepad.exe/Button[@name='Save']",
            "-d", "Save button",
        ])
        result = runner.invoke(main, [
            "selector", "load", "notepad", "save-btn", "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["selector"] == "app://notepad.exe/Button[@name='Save']"
        assert data["source"] == "user"
        assert data["description"] == "Save button"

    def test_load_builtin_fallback(self, runner, tmp_selectors, tmp_builtin):
        result = runner.invoke(main, [
            "selector", "load", "notepad", "edit-area", "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["source"] == "builtin"

    def test_load_user_takes_priority_over_builtin(self, runner, tmp_selectors, tmp_builtin):
        # Save user selector with same name as builtin
        runner.invoke(main, [
            "selector", "save", "notepad", "edit-area",
            "app://notepad.exe/Edit[@name='Custom']",
        ])
        result = runner.invoke(main, [
            "selector", "load", "notepad", "edit-area", "--json",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["source"] == "user"
        assert "Custom" in data["selector"]


# ── resolve_named_selector ──────────────────────────────────────────────────


class TestResolveNamedSelector:
    def test_resolve_user_selector(self, tmp_selectors):
        # Write selector file directly
        data = {"btn": {"selector": "app://test.exe/Button", "description": ""}}
        (tmp_selectors / "testapp.json").write_text(json.dumps(data))
        result = selector_cmd.resolve_named_selector("@testapp/btn")
        assert result == "app://test.exe/Button"

    def test_resolve_without_at_prefix(self, tmp_selectors):
        data = {"btn": {"selector": "app://test.exe/Button", "description": ""}}
        (tmp_selectors / "testapp.json").write_text(json.dumps(data))
        result = selector_cmd.resolve_named_selector("testapp/btn")
        assert result == "app://test.exe/Button"

    def test_resolve_not_found_raises_key_error(self, tmp_selectors):
        with pytest.raises(KeyError, match="Selector not found"):
            selector_cmd.resolve_named_selector("@noapp/nosel")

    def test_resolve_invalid_format_raises_value_error(self, tmp_selectors):
        with pytest.raises(ValueError, match="expected @app/name"):
            selector_cmd.resolve_named_selector("@invalid")

    def test_resolve_empty_parts_raises_value_error(self, tmp_selectors):
        with pytest.raises(ValueError, match="must be non-empty"):
            selector_cmd.resolve_named_selector("@/name")


# ── @app/name resolution in interaction commands ────────────────────────────


class TestSelectorRefResolution:
    """Test @app/name resolution in _resolve_selector_target."""

    def test_at_ref_resolved_before_parse(self, tmp_selectors):
        """Verify resolve_named_selector is called for @ references."""
        data = {"btn": {"selector": "app://notepad.exe/Button[@name='OK']", "description": ""}}
        (tmp_selectors / "notepad.json").write_text(json.dumps(data))
        resolved = selector_cmd.resolve_named_selector("@notepad/btn")
        assert resolved == "app://notepad.exe/Button[@name='OK']"

    def test_at_ref_builtin_resolved(self, tmp_selectors, tmp_builtin):
        """Verify builtin selectors are resolved via @ references."""
        resolved = selector_cmd.resolve_named_selector("@notepad/edit-area")
        assert "notepad.exe" in resolved


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

    def test_clear_no_selectors_json_exit_code(self, runner, tmp_selectors):
        """#781: selector clear --json must exit non-zero when no selectors exist."""
        result = runner.invoke(main, ["selector", "clear", "nonexistent", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False

    def test_clear_no_selectors_text_exit_code(self, runner, tmp_selectors):
        """selector clear (text mode) exits non-zero when no selectors exist."""
        result = runner.invoke(main, ["selector", "clear", "nonexistent"])
        assert result.exit_code != 0
        assert "No selectors" in result.output


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

    def test_export_no_selectors_json_exit_code(self, runner, tmp_selectors):
        """#781: selector export --json must exit non-zero when no selectors exist."""
        result = runner.invoke(main, ["selector", "export", "nonexistent", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False


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
        assert "load" in result.output
        assert "list" in result.output
        assert "export" in result.output
        assert "import" in result.output
        assert "test" in result.output

    def test_selector_load_help(self, runner):
        result = runner.invoke(main, ["selector", "load", "--help"])
        assert result.exit_code == 0

    def test_selector_save_help(self, runner):
        result = runner.invoke(main, ["selector", "save", "--help"])
        assert result.exit_code == 0

    def test_selector_import_help(self, runner):
        result = runner.invoke(main, ["selector", "import", "--help"])
        assert result.exit_code == 0


# ── JSON exit code (#781) ───────────────────────────────────────────────────


class TestJsonExitCode:
    """selector clear and selector export must exit non-zero when emitting
    {"success": false} in JSON mode (#781)."""

    def test_clear_no_selectors_json_exits_nonzero(self, runner, tmp_selectors):
        result = runner.invoke(main, ["selector", "clear", "nonexistent", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False

    def test_clear_no_selectors_text_exits_nonzero(self, runner, tmp_selectors):
        result = runner.invoke(main, ["selector", "clear", "nonexistent"])
        assert result.exit_code != 0

    def test_export_no_selectors_json_exits_nonzero(self, runner, tmp_selectors):
        with patch.object(selector_cmd, "BUILTIN_DIR", tmp_selectors / "empty_builtin"):
            result = runner.invoke(main, ["selector", "export", "nonexistent", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False

    def test_export_no_selectors_text_exits_nonzero(self, runner, tmp_selectors):
        with patch.object(selector_cmd, "BUILTIN_DIR", tmp_selectors / "empty_builtin"):
            result = runner.invoke(main, ["selector", "export", "nonexistent"])
        assert result.exit_code != 0
