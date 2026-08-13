"""MCP tools for Excel COM automation."""
from __future__ import annotations

from typing import Any, Optional


def register_excel_tools(server, _get_backend, _safe_tool):
    """Register Excel COM MCP tools."""

    @server.tool()
    @_safe_tool
    def excel_open(
        path: str,
        visible: bool = False,
        read_only: bool = False,
    ) -> dict:
        """Open an Excel workbook and return its info.

        Args:
            path: Path to the .xlsx/.xls file.
            visible: Show the Excel window.
            read_only: Open in read-only mode.

        Returns:
            Dict with path, sheets, sheet_count, active_sheet.
        """
        from naturo.excel import excel_open as _excel_open
        result = _excel_open(path, visible=visible, read_only=read_only)
        return {"success": True, **result}

    @server.tool()
    @_safe_tool
    def excel_read(
        path: str,
        cell: str,
        sheet: Optional[str] = None,
    ) -> dict:
        """Read a cell or range value from an Excel workbook.

        Args:
            path: Path to the .xlsx/.xls file.
            cell: Cell reference (e.g. 'A1') or range (e.g. 'A1:C10').
            sheet: Sheet name (default: active sheet).

        Returns:
            Dict with cell, value, sheet, type.
        """
        from naturo.excel import excel_read as _excel_read
        result = _excel_read(path, cell, sheet=sheet)
        return {"success": True, **result}

    @server.tool()
    @_safe_tool
    def excel_write(
        path: str,
        cell: str,
        value: str,
        sheet: Optional[str] = None,
        create: bool = False,
    ) -> dict:
        """Write a value to a cell in an Excel workbook.

        Args:
            path: Path to the .xlsx/.xls file.
            cell: Cell reference (e.g. 'A1').
            value: Value to write (string or number as string).
            sheet: Sheet name (default: active sheet).
            create: Create workbook if it doesn't exist.

        Returns:
            Dict with cell, sheet, path.
        """
        # Try to convert numeric values
        write_value: Any = value
        try:
            write_value = int(value)
        except ValueError:
            try:
                write_value = float(value)
            except ValueError:
                pass

        from naturo.excel import excel_write as _excel_write
        result = _excel_write(path, cell, write_value, sheet=sheet, create=create)
        return {"success": True, **result}

    @server.tool()
    @_safe_tool
    def excel_list_sheets(path: str) -> dict:
        """List all sheets in an Excel workbook.

        Args:
            path: Path to the .xlsx/.xls file.

        Returns:
            Dict with sheets list, count, active_sheet.
        """
        from naturo.excel import excel_list_sheets as _excel_list_sheets
        result = _excel_list_sheets(path)
        return {"success": True, **result}

    @server.tool()
    @_safe_tool
    def excel_run_macro(
        path: str,
        macro_name: str,
        args: Optional[list[str]] = None,
    ) -> dict:
        """Run a VBA macro in an Excel workbook.

        Args:
            path: Path to the .xlsm/.xls file.
            macro_name: Macro name (e.g. 'Module1.MyMacro').
            args: Optional list of arguments.

        Returns:
            Dict with macro name, result.
        """
        from naturo.excel import excel_run_macro as _excel_run_macro
        result = _excel_run_macro(path, macro_name, args=args)
        return {"success": True, **result}

    @server.tool()
    @_safe_tool
    def excel_create_chart(
        path: str,
        data_range: str,
        chart_type: str = "column",
        sheet: Optional[str] = None,
        title: Optional[str] = None,
        anchor: Optional[str] = None,
        create: bool = False,
    ) -> dict:
        """Create a chart from a data range in an Excel workbook.

        Args:
            path: Path to the .xlsx/.xlsm file.
            data_range: Source data range (e.g. 'A1:B10').
            chart_type: bar/column/line/pie/area/scatter (default: column).
            sheet: Sheet name (default: active sheet).
            title: Optional chart title.
            anchor: Optional cell to anchor the chart top-left (e.g. 'D2').
            create: Create the workbook if it doesn't exist.

        Returns:
            Dict with chart name, chart_type, range, sheet, anchor, position.
        """
        from naturo.excel import excel_create_chart as _excel_create_chart
        result = _excel_create_chart(
            path, data_range, chart_type=chart_type, sheet=sheet,
            title=title, anchor=anchor, create=create,
        )
        return {"success": True, **result}

    @server.tool()
    @_safe_tool
    def excel_info(
        path: str,
        sheet: Optional[str] = None,
    ) -> dict:
        """Get used range info for an Excel worksheet.

        Args:
            path: Path to the .xlsx/.xls file.
            sheet: Sheet name (default: active sheet).

        Returns:
            Dict with used_range, rows, columns.
        """
        from naturo.excel import excel_get_range_info
        result = excel_get_range_info(path, sheet=sheet)
        return {"success": True, **result}
