"""Tests for naturo.mcp._excel — MCP Excel COM automation tools.

Tests cover excel_open, excel_read, excel_write, excel_list_sheets,
excel_run_macro, excel_info with mocked naturo.excel functions.
All tests run on Linux CI (no Windows/COM dependencies).
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest

mcp_available = True
try:
    from naturo.mcp_server import create_server
except ImportError:
    mcp_available = False

pytestmark = pytest.mark.skipif(not mcp_available, reason="mcp package not installed")


def _call_tool(server, tool_name: str, arguments: dict):
    """Helper to call an MCP tool function by name."""
    async def _run():
        return await server.call_tool(tool_name, arguments)

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()


@pytest.fixture
def mock_backend():
    return MagicMock()


@pytest.fixture
def server(mock_backend):
    with patch("naturo.mcp_server.get_backend", return_value=mock_backend):
        yield create_server()


# ── excel_open ───────────────────────────────────────────────────────


class TestExcelOpen:

    @patch("naturo.excel.excel_open")
    def test_success(self, mock_open, server):
        mock_open.return_value = {
            "path": "C:\\data.xlsx",
            "sheets": ["Sheet1", "Sheet2"],
            "sheet_count": 2,
            "active_sheet": "Sheet1",
        }
        result = _call_tool(server, "excel_open", {"path": "C:\\data.xlsx"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["sheets"] == ["Sheet1", "Sheet2"]
        assert data["sheet_count"] == 2
        mock_open.assert_called_once_with("C:\\data.xlsx", visible=False, read_only=False)

    @patch("naturo.excel.excel_open")
    def test_with_options(self, mock_open, server):
        mock_open.return_value = {"path": "x.xlsx", "sheets": [], "sheet_count": 0, "active_sheet": None}
        _call_tool(server, "excel_open", {"path": "x.xlsx", "visible": True, "read_only": True})
        mock_open.assert_called_once_with("x.xlsx", visible=True, read_only=True)


# ── excel_read ───────────────────────────────────────────────────────


class TestExcelRead:

    @patch("naturo.excel.excel_read")
    def test_single_cell(self, mock_read, server):
        mock_read.return_value = {"cell": "A1", "value": 42, "sheet": "Sheet1", "type": "number"}
        result = _call_tool(server, "excel_read", {"path": "data.xlsx", "cell": "A1"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["value"] == 42
        assert data["cell"] == "A1"

    @patch("naturo.excel.excel_read")
    def test_with_sheet(self, mock_read, server):
        mock_read.return_value = {"cell": "B2", "value": "hello", "sheet": "Data", "type": "string"}
        _call_tool(server, "excel_read", {"path": "data.xlsx", "cell": "B2", "sheet": "Data"})
        mock_read.assert_called_once_with("data.xlsx", "B2", sheet="Data")

    @patch("naturo.excel.excel_read")
    def test_range_read(self, mock_read, server):
        mock_read.return_value = {
            "cell": "A1:C3",
            "value": [[1, 2, 3], [4, 5, 6], [7, 8, 9]],
            "sheet": "Sheet1",
            "type": "range",
        }
        result = _call_tool(server, "excel_read", {"path": "data.xlsx", "cell": "A1:C3"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["value"] == [[1, 2, 3], [4, 5, 6], [7, 8, 9]]


# ── excel_write ──────────────────────────────────────────────────────


class TestExcelWrite:

    @patch("naturo.excel.excel_write")
    def test_write_string(self, mock_write, server):
        mock_write.return_value = {"cell": "A1", "sheet": "Sheet1", "path": "data.xlsx"}
        result = _call_tool(server, "excel_write", {
            "path": "data.xlsx", "cell": "A1", "value": "hello",
        })
        data = json.loads(result[0].text)
        assert data["success"] is True
        mock_write.assert_called_once_with("data.xlsx", "A1", "hello", sheet=None, create=False)

    @patch("naturo.excel.excel_write")
    def test_write_integer_string_converted(self, mock_write, server):
        mock_write.return_value = {"cell": "B2", "sheet": "Sheet1", "path": "data.xlsx"}
        _call_tool(server, "excel_write", {"path": "data.xlsx", "cell": "B2", "value": "42"})
        # Value should be converted to int
        mock_write.assert_called_once_with("data.xlsx", "B2", 42, sheet=None, create=False)

    @patch("naturo.excel.excel_write")
    def test_write_float_string_converted(self, mock_write, server):
        mock_write.return_value = {"cell": "C3", "sheet": "Sheet1", "path": "data.xlsx"}
        _call_tool(server, "excel_write", {"path": "data.xlsx", "cell": "C3", "value": "3.14"})
        mock_write.assert_called_once_with("data.xlsx", "C3", 3.14, sheet=None, create=False)

    @patch("naturo.excel.excel_write")
    def test_write_with_create_and_sheet(self, mock_write, server):
        mock_write.return_value = {"cell": "A1", "sheet": "New", "path": "new.xlsx"}
        _call_tool(server, "excel_write", {
            "path": "new.xlsx", "cell": "A1", "value": "test",
            "sheet": "New", "create": True,
        })
        mock_write.assert_called_once_with("new.xlsx", "A1", "test", sheet="New", create=True)


# ── excel_list_sheets ────────────────────────────────────────────────


class TestExcelListSheets:

    @patch("naturo.excel.excel_list_sheets")
    def test_lists_sheets(self, mock_list, server):
        mock_list.return_value = {
            "sheets": ["Sheet1", "Sheet2", "Data"],
            "count": 3,
            "active_sheet": "Sheet1",
        }
        result = _call_tool(server, "excel_list_sheets", {"path": "data.xlsx"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["sheets"] == ["Sheet1", "Sheet2", "Data"]
        assert data["count"] == 3


# ── excel_run_macro ──────────────────────────────────────────────────


class TestExcelRunMacro:

    @patch("naturo.excel.excel_run_macro")
    def test_run_macro_no_args(self, mock_macro, server):
        mock_macro.return_value = {"macro": "Module1.MyMacro", "result": "OK"}
        result = _call_tool(server, "excel_run_macro", {
            "path": "macros.xlsm", "macro_name": "Module1.MyMacro",
        })
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["macro"] == "Module1.MyMacro"
        mock_macro.assert_called_once_with("macros.xlsm", "Module1.MyMacro", args=None)

    @patch("naturo.excel.excel_run_macro")
    def test_run_macro_with_args(self, mock_macro, server):
        mock_macro.return_value = {"macro": "Calculate", "result": 100}
        _call_tool(server, "excel_run_macro", {
            "path": "macros.xlsm", "macro_name": "Calculate",
            "args": ["10", "20"],
        })
        mock_macro.assert_called_once_with("macros.xlsm", "Calculate", args=["10", "20"])


# ── excel_info ───────────────────────────────────────────────────────


class TestExcelInfo:

    @patch("naturo.excel.excel_get_range_info")
    def test_returns_range_info(self, mock_info, server):
        mock_info.return_value = {
            "used_range": "A1:D100",
            "rows": 100,
            "columns": 4,
        }
        result = _call_tool(server, "excel_info", {"path": "data.xlsx"})
        data = json.loads(result[0].text)
        assert data["success"] is True
        assert data["used_range"] == "A1:D100"
        assert data["rows"] == 100
        assert data["columns"] == 4

    @patch("naturo.excel.excel_get_range_info")
    def test_with_sheet(self, mock_info, server):
        mock_info.return_value = {"used_range": "A1:B10", "rows": 10, "columns": 2}
        _call_tool(server, "excel_info", {"path": "data.xlsx", "sheet": "Summary"})
        mock_info.assert_called_once_with("data.xlsx", sheet="Summary")
