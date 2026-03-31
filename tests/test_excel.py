"""Tests for Excel COM automation (Phase 5C.1).

Backend functions are tested with mocked win32com.client since Excel
is only available on Windows with Office installed. CLI integration
tests use Click's CliRunner.
"""

import json
import os
import platform
import sys
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
from click.testing import CliRunner

# ── Skip non-Windows ─────────────────────────────────────────────────────

is_windows = platform.system() == "Windows"


# ── Backend unit tests ────────────────────────────────────────────────────


class TestExcelBackend:
    """Test naturo.excel module functions with mocked COM."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self, tmp_path):
        """Set up common mocks and temp files."""
        self.test_file = tmp_path / "test.xlsx"
        self.test_file.write_bytes(b"fake xlsx content")
        self.test_path = str(self.test_file)

    @pytest.mark.skipif(not is_windows, reason="Excel COM requires Windows")
    @patch("naturo.excel._get_excel")
    def test_excel_open(self, mock_get_excel):
        """excel_open returns workbook info."""
        from naturo.excel import excel_open

        mock_excel = MagicMock()
        mock_wb = MagicMock()
        mock_wb.Sheets.Count = 2
        mock_wb.Sheets.side_effect = lambda i: MagicMock(Name=["Sheet1", "Sheet2"][i - 1])
        mock_wb.ActiveSheet.Name = "Sheet1"
        mock_excel.Workbooks.Open.return_value = mock_wb
        mock_get_excel.return_value = mock_excel

        result = excel_open(self.test_path)

        assert result["sheets"] == ["Sheet1", "Sheet2"]
        assert result["sheet_count"] == 2
        assert result["active_sheet"] == "Sheet1"

    @pytest.mark.skipif(not is_windows, reason="Excel COM requires Windows")
    @patch("naturo.excel._get_excel")
    def test_excel_read_cell(self, mock_get_excel):
        """excel_read returns single cell value."""
        from naturo.excel import excel_read

        mock_excel = MagicMock()
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_ws.Name = "Sheet1"
        mock_ws.Range.return_value = MagicMock(Value=42)
        mock_wb.ActiveSheet = mock_ws
        mock_excel.Workbooks.Open.return_value = mock_wb
        mock_get_excel.return_value = mock_excel

        result = excel_read(self.test_path, "A1")

        assert result["cell"] == "A1"
        assert result["value"] == 42
        assert result["sheet"] == "Sheet1"

    @pytest.mark.skipif(not is_windows, reason="Excel COM requires Windows")
    @patch("naturo.excel._get_excel")
    def test_excel_read_range(self, mock_get_excel):
        """excel_read returns range as 2D list."""
        from naturo.excel import excel_read

        mock_excel = MagicMock()
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_ws.Name = "Sheet1"
        mock_range = MagicMock()
        mock_range.Value = ((1, 2), (3, 4))
        mock_range.Rows.Count = 2
        mock_range.Columns.Count = 2
        mock_ws.Range.return_value = mock_range
        mock_wb.ActiveSheet = mock_ws
        mock_excel.Workbooks.Open.return_value = mock_wb
        mock_get_excel.return_value = mock_excel

        result = excel_read(self.test_path, "A1:B2")

        assert result["cell"] == "A1:B2"
        assert result["value"] == [[1, 2], [3, 4]]
        assert result["rows"] == 2
        assert result["columns"] == 2

    @pytest.mark.skipif(not is_windows, reason="Excel COM requires Windows")
    @patch("naturo.excel._get_excel")
    def test_excel_write(self, mock_get_excel):
        """excel_write writes to a cell and returns info."""
        from naturo.excel import excel_write

        mock_excel = MagicMock()
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_ws.Name = "Sheet1"
        mock_wb.ActiveSheet = mock_ws
        mock_excel.Workbooks.Open.return_value = mock_wb
        mock_get_excel.return_value = mock_excel

        result = excel_write(self.test_path, "A1", "Hello")

        assert result["cell"] == "A1"
        assert result["sheet"] == "Sheet1"
        mock_ws.Range("A1").Value = "Hello"

    @pytest.mark.skipif(not is_windows, reason="Excel COM requires Windows")
    @patch("naturo.excel._get_excel")
    def test_excel_list_sheets(self, mock_get_excel):
        """excel_list_sheets returns sheet listing."""
        from naturo.excel import excel_list_sheets

        mock_excel = MagicMock()
        mock_wb = MagicMock()
        mock_wb.Sheets.Count = 3
        mock_wb.Sheets.side_effect = lambda i: MagicMock(
            Name=["Data", "Charts", "Summary"][i - 1]
        )
        mock_wb.ActiveSheet.Name = "Data"
        mock_excel.Workbooks.Open.return_value = mock_wb
        mock_get_excel.return_value = mock_excel

        result = excel_list_sheets(self.test_path)

        assert result["sheets"] == ["Data", "Charts", "Summary"]
        assert result["count"] == 3
        assert result["active_sheet"] == "Data"

    @pytest.mark.skipif(not is_windows, reason="Excel COM requires Windows")
    @patch("naturo.excel._get_excel")
    def test_excel_run_macro(self, mock_get_excel):
        """excel_run_macro runs a macro and returns result."""
        from naturo.excel import excel_run_macro

        mock_excel = MagicMock()
        mock_wb = MagicMock()
        mock_excel.Workbooks.Open.return_value = mock_wb
        mock_excel.Application.Run.return_value = "Done"
        mock_get_excel.return_value = mock_excel

        result = excel_run_macro(self.test_path, "Module1.Test")

        assert result["macro"] == "Module1.Test"
        assert result["result"] == "Done"

    @pytest.mark.skipif(not is_windows, reason="Excel COM requires Windows")
    def test_workbook_not_found(self):
        """excel_open raises WorkbookNotFoundError for missing file."""
        from naturo.excel import excel_open, WorkbookNotFoundError

        with pytest.raises(WorkbookNotFoundError):
            excel_open("/nonexistent/file.xlsx")

    @pytest.mark.skipif(not is_windows, reason="Excel COM requires Windows")
    @patch("naturo.excel._get_excel")
    def test_sheet_not_found(self, mock_get_excel):
        """excel_read raises SheetNotFoundError for missing sheet."""
        from naturo.excel import excel_read, SheetNotFoundError

        mock_excel = MagicMock()
        mock_wb = MagicMock()
        mock_wb.Sheets.Count = 1
        mock_wb.Sheets.side_effect = lambda i: MagicMock(Name="Sheet1")
        mock_excel.Workbooks.Open.return_value = mock_wb
        mock_get_excel.return_value = mock_excel

        with pytest.raises(SheetNotFoundError) as exc_info:
            excel_read(self.test_path, "A1", sheet="NonexistentSheet")

        assert "NonexistentSheet" in str(exc_info.value)

    @pytest.mark.skipif(not is_windows, reason="Excel COM requires Windows")
    @patch("naturo.excel._get_excel")
    def test_excel_get_range_info(self, mock_get_excel):
        """excel_get_range_info returns used range dimensions."""
        from naturo.excel import excel_get_range_info

        mock_excel = MagicMock()
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_ws.Name = "Sheet1"
        mock_ws.UsedRange.Address = "$A$1:$D$10"
        mock_ws.UsedRange.Rows.Count = 10
        mock_ws.UsedRange.Columns.Count = 4
        mock_ws.UsedRange.Row = 1
        mock_ws.UsedRange.Column = 1
        mock_wb.ActiveSheet = mock_ws
        mock_excel.Workbooks.Open.return_value = mock_wb
        mock_get_excel.return_value = mock_excel

        result = excel_get_range_info(self.test_path)

        assert result["sheet"] == "Sheet1"
        assert result["rows"] == 10
        assert result["columns"] == 4


# ── Error class tests (cross-platform) ───────────────────────────────────


class TestExcelErrors:
    """Test Excel error classes (no Windows dependency)."""

    def test_excel_error_is_naturo_error(self):
        """ExcelError inherits NaturoError."""
        from naturo.excel import ExcelError
        from naturo.errors import NaturoError

        err = ExcelError("test error")
        assert isinstance(err, NaturoError)
        assert err.code == "EXCEL_ERROR"

    def test_workbook_not_found_error(self):
        """WorkbookNotFoundError has correct code."""
        from naturo.excel import WorkbookNotFoundError
        from naturo.errors import ErrorCode

        err = WorkbookNotFoundError("/path/to/file.xlsx")
        assert err.code == ErrorCode.FILE_NOT_FOUND
        assert "file.xlsx" in err.message

    def test_sheet_not_found_error(self):
        """SheetNotFoundError includes available sheets."""
        from naturo.excel import SheetNotFoundError

        err = SheetNotFoundError("Missing", available=["Sheet1", "Sheet2"])
        assert err.code == "SHEET_NOT_FOUND"
        assert err.context["available_sheets"] == ["Sheet1", "Sheet2"]

    def test_excel_not_installed_error(self):
        """ExcelNotInstalledError has suggestion."""
        from naturo.excel import ExcelNotInstalledError

        err = ExcelNotInstalledError("pywin32 missing")
        assert err.code == "EXCEL_NOT_AVAILABLE"
        assert "pywin32" in err.suggested_action

    def test_cell_value_to_python(self):
        """_cell_value_to_python handles various types."""
        from naturo.excel import _cell_value_to_python

        assert _cell_value_to_python(None) is None
        assert _cell_value_to_python(42) == 42
        assert _cell_value_to_python(3.14) == 3.14
        assert _cell_value_to_python("hello") == "hello"
        assert _cell_value_to_python(True) is True
        assert _cell_value_to_python(((1, 2), (3, 4))) == [[1, 2], [3, 4]]


# ── CLI tests (cross-platform via CliRunner) ─────────────────────────────


class TestExcelCLI:
    """Test Excel CLI commands."""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def cli(self):
        from naturo.cli import main
        return main

    def test_excel_group_help(self, runner, cli):
        """Excel group shows help text."""
        result = runner.invoke(cli, ["excel", "--help"])
        assert result.exit_code == 0
        assert "Excel COM automation" in result.output

    def test_excel_open_help(self, runner, cli):
        """Excel open shows help."""
        result = runner.invoke(cli, ["excel", "open", "--help"])
        assert result.exit_code == 0
        assert "Open an Excel workbook" in result.output

    def test_excel_read_help(self, runner, cli):
        """Excel read shows help."""
        result = runner.invoke(cli, ["excel", "read", "--help"])
        assert result.exit_code == 0
        assert "Read a cell or range" in result.output

    def test_excel_write_help(self, runner, cli):
        """Excel write shows help."""
        result = runner.invoke(cli, ["excel", "write", "--help"])
        assert result.exit_code == 0
        assert "Write a value" in result.output

    def test_excel_list_sheets_help(self, runner, cli):
        """Excel list-sheets shows help."""
        result = runner.invoke(cli, ["excel", "list-sheets", "--help"])
        assert result.exit_code == 0
        assert "List all sheets" in result.output

    def test_excel_run_macro_help(self, runner, cli):
        """Excel run-macro shows help."""
        result = runner.invoke(cli, ["excel", "run-macro", "--help"])
        assert result.exit_code == 0
        assert "Run a VBA macro" in result.output

    def test_excel_info_help(self, runner, cli):
        """Excel info shows help."""
        result = runner.invoke(cli, ["excel", "info", "--help"])
        assert result.exit_code == 0
        assert "used range" in result.output.lower()

    @pytest.mark.skipif(not is_windows, reason="Excel COM requires Windows")
    def test_excel_read_nonexistent_file_json(self, runner, cli):
        """Excel read on missing file returns JSON error."""
        result = runner.invoke(cli, ["excel", "read", "/nonexistent.xlsx", "A1", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False
        assert data["error"]["code"] in ("FILE_NOT_FOUND", "EXCEL_ERROR")

    @pytest.mark.skipif(not is_windows, reason="Excel COM requires Windows")
    def test_excel_write_nonexistent_file_json(self, runner, cli):
        """Excel write on missing file without --create returns JSON error."""
        result = runner.invoke(cli, ["excel", "write", "/nonexistent.xlsx", "A1", "test", "--json"])
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["success"] is False

    def test_excel_subcommands_present(self, runner, cli):
        """All expected Excel subcommands are registered."""
        result = runner.invoke(cli, ["excel", "--help"])
        assert result.exit_code == 0
        for cmd in ["open", "read", "write", "list-sheets", "run-macro", "info"]:
            assert cmd in result.output, f"Missing subcommand: {cmd}"


# ── MCP tool tests ────────────────────────────────────────────────────────


class TestExcelMCP:
    """Test Excel MCP tool registration."""

    def test_excel_mcp_tools_registered(self):
        """Excel MCP tools are registered in create_server."""
        pytest.importorskip("mcp")

        from naturo.mcp_server import create_server

        server = create_server()
        # Check tool names include excel tools
        tool_names = [t.name for t in server._tool_manager.list_tools()]
        expected = ["excel_open", "excel_read", "excel_write",
                     "excel_list_sheets", "excel_run_macro", "excel_info"]
        for name in expected:
            assert name in tool_names, f"MCP tool '{name}' not registered"
