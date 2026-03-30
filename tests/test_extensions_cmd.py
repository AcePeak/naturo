"""Tests for naturo.cli.extensions — excel open, read, write, list-sheets, run-macro, info."""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from naturo.cli.extensions import excel


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# excel open
# ---------------------------------------------------------------------------

class TestExcelOpen:
    """Tests for 'naturo excel open' command."""

    def test_open_success(self, runner):
        result_data = {
            "path": "report.xlsx",
            "sheet_count": 3,
            "sheets": ["Sheet1", "Sheet2", "Sheet3"],
            "active_sheet": "Sheet1",
        }
        with patch("naturo.cli.extensions.excel_open", return_value=result_data, create=True), \
             patch("naturo.excel.excel_open", return_value=result_data, create=True):
            result = runner.invoke(excel, ["open", "report.xlsx"])
        assert result.exit_code == 0
        assert "report.xlsx" in result.output

    def test_open_json(self, runner):
        result_data = {
            "path": "report.xlsx",
            "sheet_count": 2,
            "sheets": ["Sales", "Summary"],
            "active_sheet": "Sales",
        }
        with patch("naturo.excel.excel_open", return_value=result_data, create=True):
            result = runner.invoke(excel, ["open", "report.xlsx", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["sheet_count"] == 2

    def test_open_visible(self, runner):
        result_data = {"path": "x.xlsx", "sheet_count": 1, "sheets": ["Sheet1"], "active_sheet": "Sheet1"}
        with patch("naturo.excel.excel_open", return_value=result_data, create=True) as mock_open:
            result = runner.invoke(excel, ["open", "x.xlsx", "--visible"])
        assert result.exit_code == 0
        mock_open.assert_called_once_with("x.xlsx", visible=True, read_only=False)

    def test_open_error(self, runner):
        with patch("naturo.excel.excel_open", side_effect=FileNotFoundError("not found"), create=True):
            result = runner.invoke(excel, ["open", "missing.xlsx"])
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_open_missing_path(self, runner):
        result = runner.invoke(excel, ["open"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# excel read
# ---------------------------------------------------------------------------

class TestExcelRead:
    """Tests for 'naturo excel read' command."""

    def test_read_single_cell(self, runner):
        result_data = {"cell": "A1", "sheet": "Sheet1", "value": "Hello"}
        with patch("naturo.excel.excel_read", return_value=result_data, create=True):
            result = runner.invoke(excel, ["read", "data.xlsx", "A1"])
        assert result.exit_code == 0
        assert "Hello" in result.output

    def test_read_range(self, runner):
        result_data = {"cell": "A1:B2", "sheet": "Sheet1", "value": [["a", "b"], ["c", "d"]]}
        with patch("naturo.excel.excel_read", return_value=result_data, create=True):
            result = runner.invoke(excel, ["read", "data.xlsx", "A1:B2"])
        assert result.exit_code == 0
        assert "a" in result.output

    def test_read_json(self, runner):
        result_data = {"cell": "A1", "sheet": "Sheet1", "value": 42}
        with patch("naturo.excel.excel_read", return_value=result_data, create=True):
            result = runner.invoke(excel, ["read", "data.xlsx", "A1", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["value"] == 42

    def test_read_with_sheet(self, runner):
        result_data = {"cell": "B2", "sheet": "Sales", "value": 100}
        with patch("naturo.excel.excel_read", return_value=result_data, create=True) as mock_read:
            result = runner.invoke(excel, ["read", "data.xlsx", "B2", "--sheet", "Sales"])
        assert result.exit_code == 0
        mock_read.assert_called_once_with("data.xlsx", "B2", sheet="Sales")

    def test_read_error(self, runner):
        with patch("naturo.excel.excel_read", side_effect=RuntimeError("locked"), create=True):
            result = runner.invoke(excel, ["read", "data.xlsx", "A1"])
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_read_range_with_none(self, runner):
        result_data = {"cell": "A1:B2", "sheet": "Sheet1", "value": [[None, "b"], ["c", None]]}
        with patch("naturo.excel.excel_read", return_value=result_data, create=True):
            result = runner.invoke(excel, ["read", "data.xlsx", "A1:B2"])
        assert result.exit_code == 0
        assert "b" in result.output


# ---------------------------------------------------------------------------
# excel write
# ---------------------------------------------------------------------------

class TestExcelWrite:
    """Tests for 'naturo excel write' command."""

    def test_write_text(self, runner):
        result_data = {"cell": "A1", "sheet": "Sheet1"}
        with patch("naturo.excel.excel_write", return_value=result_data, create=True):
            result = runner.invoke(excel, ["write", "data.xlsx", "A1", "Hello"])
        assert result.exit_code == 0
        assert "Wrote to A1" in result.output

    def test_write_numeric_int(self, runner):
        result_data = {"cell": "B1", "sheet": "Sheet1"}
        with patch("naturo.excel.excel_write", return_value=result_data, create=True) as mock_write:
            result = runner.invoke(excel, ["write", "data.xlsx", "B1", "42"])
        assert result.exit_code == 0
        # Value should be converted to int
        mock_write.assert_called_once_with("data.xlsx", "B1", 42, sheet=None, create=False)

    def test_write_numeric_float(self, runner):
        result_data = {"cell": "C1", "sheet": "Sheet1"}
        with patch("naturo.excel.excel_write", return_value=result_data, create=True) as mock_write:
            result = runner.invoke(excel, ["write", "data.xlsx", "C1", "3.14"])
        assert result.exit_code == 0
        mock_write.assert_called_once_with("data.xlsx", "C1", 3.14, sheet=None, create=False)

    def test_write_json(self, runner):
        result_data = {"cell": "A1", "sheet": "Sheet1"}
        with patch("naturo.excel.excel_write", return_value=result_data, create=True):
            result = runner.invoke(excel, ["write", "data.xlsx", "A1", "test", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True

    def test_write_with_create(self, runner):
        result_data = {"cell": "A1", "sheet": "Sheet1"}
        with patch("naturo.excel.excel_write", return_value=result_data, create=True) as mock_write:
            result = runner.invoke(excel, ["write", "new.xlsx", "A1", "data", "--create"])
        mock_write.assert_called_once_with("new.xlsx", "A1", "data", sheet=None, create=True)

    def test_write_error(self, runner):
        with patch("naturo.excel.excel_write", side_effect=RuntimeError("fail"), create=True):
            result = runner.invoke(excel, ["write", "data.xlsx", "A1", "x"])
        assert result.exit_code != 0 or "error" in result.output.lower()


# ---------------------------------------------------------------------------
# excel list-sheets
# ---------------------------------------------------------------------------

class TestExcelListSheets:
    """Tests for 'naturo excel list-sheets' command."""

    def test_list_sheets(self, runner):
        result_data = {"path": "data.xlsx", "sheets": ["Sheet1", "Sheet2"], "active_sheet": "Sheet1"}
        with patch("naturo.excel.excel_list_sheets", return_value=result_data, create=True):
            result = runner.invoke(excel, ["list-sheets", "data.xlsx"])
        assert result.exit_code == 0
        assert "Sheet1" in result.output
        assert "(active)" in result.output

    def test_list_sheets_json(self, runner):
        result_data = {"path": "data.xlsx", "sheets": ["Sales"], "active_sheet": "Sales"}
        with patch("naturo.excel.excel_list_sheets", return_value=result_data, create=True):
            result = runner.invoke(excel, ["list-sheets", "data.xlsx", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True

    def test_list_sheets_error(self, runner):
        with patch("naturo.excel.excel_list_sheets", side_effect=FileNotFoundError("no file"), create=True):
            result = runner.invoke(excel, ["list-sheets", "missing.xlsx"])
        assert result.exit_code != 0 or "error" in result.output.lower()


# ---------------------------------------------------------------------------
# excel run-macro
# ---------------------------------------------------------------------------

class TestExcelRunMacro:
    """Tests for 'naturo excel run-macro' command."""

    def test_run_macro(self, runner):
        result_data = {"macro": "Module1.Format", "result": None}
        with patch("naturo.excel.excel_run_macro", return_value=result_data, create=True):
            result = runner.invoke(excel, ["run-macro", "report.xlsm", "Module1.Format"])
        assert result.exit_code == 0
        assert "executed" in result.output

    def test_run_macro_with_result(self, runner):
        result_data = {"macro": "CalcSum", "result": 42}
        with patch("naturo.excel.excel_run_macro", return_value=result_data, create=True):
            result = runner.invoke(excel, ["run-macro", "data.xlsm", "CalcSum"])
        assert result.exit_code == 0
        assert "42" in result.output

    def test_run_macro_with_args(self, runner):
        result_data = {"macro": "Update", "result": None}
        with patch("naturo.excel.excel_run_macro", return_value=result_data, create=True) as mock_run:
            result = runner.invoke(excel, ["run-macro", "data.xlsm", "Update", "--arg", "2024", "--arg", "Q1"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with("data.xlsm", "Update", args=["2024", "Q1"])

    def test_run_macro_json(self, runner):
        result_data = {"macro": "Fmt", "result": "done"}
        with patch("naturo.excel.excel_run_macro", return_value=result_data, create=True):
            result = runner.invoke(excel, ["run-macro", "r.xlsm", "Fmt", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True

    def test_run_macro_error(self, runner):
        with patch("naturo.excel.excel_run_macro", side_effect=RuntimeError("macro error"), create=True):
            result = runner.invoke(excel, ["run-macro", "r.xlsm", "Bad"])
        assert result.exit_code != 0 or "error" in result.output.lower()


# ---------------------------------------------------------------------------
# excel info
# ---------------------------------------------------------------------------

class TestExcelInfo:
    """Tests for 'naturo excel info' command."""

    def test_info(self, runner):
        result_data = {"sheet": "Sheet1", "used_range": "A1:D100", "rows": 100, "columns": 4}
        with patch("naturo.excel.excel_get_range_info", return_value=result_data, create=True):
            result = runner.invoke(excel, ["info", "data.xlsx"])
        assert result.exit_code == 0
        assert "A1:D100" in result.output
        assert "100" in result.output

    def test_info_json(self, runner):
        result_data = {"sheet": "Sales", "used_range": "A1:B10", "rows": 10, "columns": 2}
        with patch("naturo.excel.excel_get_range_info", return_value=result_data, create=True):
            result = runner.invoke(excel, ["info", "data.xlsx", "--json"])
        data = json.loads(result.output)
        assert data["success"] is True
        assert data["rows"] == 10

    def test_info_with_sheet(self, runner):
        result_data = {"sheet": "Sales", "used_range": "A1:C5", "rows": 5, "columns": 3}
        with patch("naturo.excel.excel_get_range_info", return_value=result_data, create=True) as mock_info:
            result = runner.invoke(excel, ["info", "data.xlsx", "--sheet", "Sales"])
        mock_info.assert_called_once_with("data.xlsx", sheet="Sales")

    def test_info_error(self, runner):
        with patch("naturo.excel.excel_get_range_info", side_effect=RuntimeError("fail"), create=True):
            result = runner.invoke(excel, ["info", "missing.xlsx"])
        assert result.exit_code != 0 or "error" in result.output.lower()


# ---------------------------------------------------------------------------
# Help
# ---------------------------------------------------------------------------

class TestExcelHelp:
    """Tests for excel command help text."""

    def test_excel_help(self, runner):
        result = runner.invoke(excel, ["--help"])
        assert result.exit_code == 0
        assert "open" in result.output
        assert "read" in result.output
        assert "write" in result.output

    def test_open_help(self, runner):
        result = runner.invoke(excel, ["open", "--help"])
        assert result.exit_code == 0
        assert "--visible" in result.output

    def test_read_help(self, runner):
        result = runner.invoke(excel, ["read", "--help"])
        assert result.exit_code == 0
        assert "CELL" in result.output
