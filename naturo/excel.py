"""Windows Excel COM Automation backend.

Provides read/write cells, list sheets, run macros, and workbook management
using ``win32com.client`` (pywin32). All functions return structured dicts
for easy JSON serialisation by the CLI layer.

Phase 5C.1 — Excel COM Automation.

Requires:
    - Windows OS
    - Microsoft Excel installed
    - pywin32 (``pip install pywin32``)
"""

from __future__ import annotations

import os
import platform
from typing import Any

from naturo.errors import NaturoError, ErrorCode, ErrorCategory


# ── Error classes ────────────────────────────────────────────────────────────


class ExcelError(NaturoError):
    """Excel COM automation error."""

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault("category", ErrorCategory.AUTOMATION)
        super().__init__(message, code=kwargs.pop("code", "EXCEL_ERROR"), **kwargs)


class ExcelNotInstalledError(ExcelError):
    """Excel or pywin32 is not available."""

    def __init__(self, detail: str = "") -> None:
        msg = "Microsoft Excel is not available"
        if detail:
            msg += f": {detail}"
        super().__init__(
            msg,
            code="EXCEL_NOT_AVAILABLE",
            suggested_action="Install Microsoft Excel and pywin32 (pip install pywin32).",
        )


class WorkbookNotFoundError(ExcelError):
    """Workbook file not found."""

    def __init__(self, path: str) -> None:
        super().__init__(
            f"Workbook not found: {path}",
            code=ErrorCode.FILE_NOT_FOUND,
            context={"path": path},
        )


class SheetNotFoundError(ExcelError):
    """Worksheet not found."""

    def __init__(self, sheet: str, available: list[str] | None = None) -> None:
        ctx: dict[str, Any] = {"sheet": sheet}
        if available:
            ctx["available_sheets"] = available
        super().__init__(
            f"Sheet not found: {sheet}",
            code="SHEET_NOT_FOUND",
            context=ctx,
            suggested_action=f"Available sheets: {', '.join(available)}" if available else None,
        )


# ── Helpers ──────────────────────────────────────────────────────────────────


def _require_windows() -> None:
    """Raise if not on Windows."""
    if platform.system() != "Windows":
        raise ExcelError(
            "Excel COM automation requires Windows",
            code=ErrorCode.PERMISSION_DENIED,
        )


def _require_pywin32():  # type: ignore[no-untyped-def]
    """Import and return win32com.client, raising a clear error if unavailable."""
    try:
        import win32com.client  # type: ignore[import-untyped]
        return win32com.client
    except ImportError:
        raise ExcelNotInstalledError("pywin32 is not installed (pip install pywin32)")


def _get_excel(visible: bool = False):  # type: ignore[no-untyped-def]
    """Get or create an Excel COM instance.

    Args:
        visible: Whether to show the Excel window.

    Returns:
        Excel Application COM object.

    Raises:
        ExcelNotInstalledError: If Excel or pywin32 is unavailable.
    """
    _require_windows()
    win32com_client = _require_pywin32()

    try:
        excel = win32com_client.Dispatch("Excel.Application")
    except Exception as exc:
        raise ExcelNotInstalledError(str(exc))

    excel.Visible = visible
    excel.DisplayAlerts = False
    return excel


def _normalize_path(path: str) -> str:
    """Convert to absolute path with forward slashes replaced.

    Args:
        path: File path (relative or absolute).

    Returns:
        Absolute path string.
    """
    return os.path.abspath(os.path.expanduser(path))


def _get_sheet_names(workbook: Any) -> list[str]:
    """Extract sheet names from a workbook COM object.

    Args:
        workbook: Excel Workbook COM object.

    Returns:
        List of sheet name strings.
    """
    return [workbook.Sheets(i + 1).Name for i in range(workbook.Sheets.Count)]


def _get_worksheet(workbook: Any, sheet: str | None) -> Any:
    """Get a worksheet by name, or the active sheet if name is None.

    Args:
        workbook: Excel Workbook COM object.
        sheet: Sheet name, or None for active sheet.

    Returns:
        Worksheet COM object.

    Raises:
        SheetNotFoundError: If the named sheet does not exist.
    """
    if sheet is None:
        return workbook.ActiveSheet

    names = _get_sheet_names(workbook)
    # Case-insensitive match
    for name in names:
        if name.lower() == sheet.lower():
            return workbook.Sheets(name)

    raise SheetNotFoundError(sheet, available=names)


def _cell_value_to_python(value: Any) -> Any:
    """Convert a COM cell value to a JSON-serialisable Python type.

    Args:
        value: Raw COM cell value.

    Returns:
        Converted value (str, int, float, bool, None, or list for ranges).
    """
    if value is None:
        return None
    if isinstance(value, (int, float, bool, str)):
        return value

    # pywintypes.datetime → ISO string
    try:
        if hasattr(value, "isoformat"):
            return value.isoformat()
    except Exception:
        pass

    # Tuple of tuples (range) → list of lists
    if isinstance(value, tuple):
        result = []
        for row in value:
            if isinstance(row, tuple):
                result.append([_cell_value_to_python(c) for c in row])
            else:
                result.append(_cell_value_to_python(row))
        return result

    return str(value)


# ── Public API ───────────────────────────────────────────────────────────────


def excel_open(
    path: str,
    visible: bool = False,
    read_only: bool = False,
) -> dict[str, Any]:
    """Open an Excel workbook.

    Args:
        path: Path to the .xlsx/.xls file.
        visible: Show the Excel window.
        read_only: Open in read-only mode.

    Returns:
        Dict with workbook info (path, sheets, active_sheet).

    Raises:
        WorkbookNotFoundError: If the file does not exist.
        ExcelError: If Excel fails to open the file.
    """
    _require_windows()
    abs_path = _normalize_path(path)

    if not os.path.isfile(abs_path):
        raise WorkbookNotFoundError(path)

    excel = _get_excel(visible=visible)
    try:
        wb = excel.Workbooks.Open(abs_path, ReadOnly=read_only)
    except Exception as exc:
        raise ExcelError(f"Failed to open workbook: {exc}", context={"path": abs_path})

    sheets = _get_sheet_names(wb)
    active = wb.ActiveSheet.Name

    return {
        "path": abs_path,
        "sheets": sheets,
        "sheet_count": len(sheets),
        "active_sheet": active,
    }


def excel_read(
    path: str,
    cell: str,
    sheet: str | None = None,
) -> dict[str, Any]:
    """Read a cell or range from an Excel workbook.

    Args:
        path: Path to the .xlsx/.xls file.
        cell: Cell reference (e.g., 'A1') or range (e.g., 'A1:C10').
        sheet: Sheet name (default: active sheet).

    Returns:
        Dict with cell, value, sheet, and type info.

    Raises:
        WorkbookNotFoundError: If the file does not exist.
        SheetNotFoundError: If the sheet does not exist.
        ExcelError: If reading fails.
    """
    _require_windows()
    abs_path = _normalize_path(path)

    if not os.path.isfile(abs_path):
        raise WorkbookNotFoundError(path)

    excel = _get_excel(visible=False)
    try:
        wb = excel.Workbooks.Open(abs_path, ReadOnly=True)
        ws = _get_worksheet(wb, sheet)

        rng = ws.Range(cell)
        raw_value = rng.Value

        value = _cell_value_to_python(raw_value)

        # Determine if it's a single cell or range
        is_range = ":" in cell
        result: dict[str, Any] = {
            "cell": cell,
            "sheet": ws.Name,
            "value": value,
        }

        if is_range:
            result["rows"] = rng.Rows.Count
            result["columns"] = rng.Columns.Count
        else:
            # Single cell — include type info
            result["type"] = type(raw_value).__name__ if raw_value is not None else "empty"

        wb.Close(SaveChanges=False)
        return result

    except (WorkbookNotFoundError, SheetNotFoundError):
        raise
    except Exception as exc:
        raise ExcelError(f"Failed to read cell {cell}: {exc}", context={"cell": cell})
    finally:
        try:
            excel.Quit()
        except Exception:
            pass


def excel_write(
    path: str,
    cell: str,
    value: Any,
    sheet: str | None = None,
    create: bool = False,
) -> dict[str, Any]:
    """Write a value to a cell or range in an Excel workbook.

    Args:
        path: Path to the .xlsx/.xls file.
        cell: Cell reference (e.g., 'A1') or range start.
        value: Value to write (string, number, or 2D list for ranges).
        sheet: Sheet name (default: active sheet).
        create: Create the file if it doesn't exist.

    Returns:
        Dict with cell, value, and sheet info.

    Raises:
        WorkbookNotFoundError: If the file does not exist and create is False.
        SheetNotFoundError: If the sheet does not exist.
        ExcelError: If writing fails.
    """
    _require_windows()
    abs_path = _normalize_path(path)

    if not os.path.isfile(abs_path) and not create:
        raise WorkbookNotFoundError(path)

    excel = _get_excel(visible=False)
    try:
        if os.path.isfile(abs_path):
            wb = excel.Workbooks.Open(abs_path)
        else:
            wb = excel.Workbooks.Add()

        ws = _get_worksheet(wb, sheet)

        # Write value
        if isinstance(value, list) and all(isinstance(row, list) for row in value):
            # 2D array → range write
            rows = len(value)
            cols = max(len(row) for row in value) if value else 0
            # Pad rows to same length
            padded = [row + [None] * (cols - len(row)) for row in value]

            start_range = ws.Range(cell)
            end_range = ws.Cells(start_range.Row + rows - 1, start_range.Column + cols - 1)
            target = ws.Range(start_range, end_range)
            target.Value = padded

            written = {"type": "range", "rows": rows, "columns": cols}
        else:
            ws.Range(cell).Value = value
            written = {"type": "cell", "value": value}

        # Save
        if os.path.isfile(abs_path):
            wb.Save()
        else:
            wb.SaveAs(abs_path)

        wb.Close(SaveChanges=False)

        return {
            "cell": cell,
            "sheet": ws.Name,
            "path": abs_path,
            **written,
        }

    except (WorkbookNotFoundError, SheetNotFoundError):
        raise
    except Exception as exc:
        raise ExcelError(f"Failed to write to cell {cell}: {exc}", context={"cell": cell})
    finally:
        try:
            excel.Quit()
        except Exception:
            pass


def excel_list_sheets(path: str) -> dict[str, Any]:
    """List all sheets in a workbook.

    Args:
        path: Path to the .xlsx/.xls file.

    Returns:
        Dict with sheets list, count, and active sheet name.

    Raises:
        WorkbookNotFoundError: If the file does not exist.
    """
    _require_windows()
    abs_path = _normalize_path(path)

    if not os.path.isfile(abs_path):
        raise WorkbookNotFoundError(path)

    excel = _get_excel(visible=False)
    try:
        wb = excel.Workbooks.Open(abs_path, ReadOnly=True)
        sheets = _get_sheet_names(wb)
        active = wb.ActiveSheet.Name
        wb.Close(SaveChanges=False)

        return {
            "path": abs_path,
            "sheets": sheets,
            "count": len(sheets),
            "active_sheet": active,
        }
    except WorkbookNotFoundError:
        raise
    except Exception as exc:
        raise ExcelError(f"Failed to list sheets: {exc}", context={"path": abs_path})
    finally:
        try:
            excel.Quit()
        except Exception:
            pass


def excel_run_macro(
    path: str,
    macro_name: str,
    args: list[Any] | None = None,
) -> dict[str, Any]:
    """Run a VBA macro in an Excel workbook.

    Args:
        path: Path to the .xlsm/.xls file with macros.
        macro_name: Macro name (e.g., 'Module1.MyMacro').
        args: Optional list of arguments to pass to the macro.

    Returns:
        Dict with macro name, result, and path.

    Raises:
        WorkbookNotFoundError: If the file does not exist.
        ExcelError: If the macro fails.
    """
    _require_windows()
    abs_path = _normalize_path(path)

    if not os.path.isfile(abs_path):
        raise WorkbookNotFoundError(path)

    excel = _get_excel(visible=False)
    try:
        wb = excel.Workbooks.Open(abs_path)

        if args:
            result = excel.Application.Run(macro_name, *args)
        else:
            result = excel.Application.Run(macro_name)

        wb.Save()
        wb.Close(SaveChanges=False)

        return {
            "macro": macro_name,
            "path": abs_path,
            "result": _cell_value_to_python(result),
        }

    except WorkbookNotFoundError:
        raise
    except Exception as exc:
        raise ExcelError(
            f"Failed to run macro '{macro_name}': {exc}",
            context={"macro": macro_name, "path": abs_path},
        )
    finally:
        try:
            excel.Quit()
        except Exception:
            pass


def excel_get_range_info(
    path: str,
    sheet: str | None = None,
) -> dict[str, Any]:
    """Get info about the used range of a sheet.

    Args:
        path: Path to the .xlsx/.xls file.
        sheet: Sheet name (default: active sheet).

    Returns:
        Dict with used range dimensions, row/column counts.

    Raises:
        WorkbookNotFoundError: If the file does not exist.
        SheetNotFoundError: If the sheet does not exist.
    """
    _require_windows()
    abs_path = _normalize_path(path)

    if not os.path.isfile(abs_path):
        raise WorkbookNotFoundError(path)

    excel = _get_excel(visible=False)
    try:
        wb = excel.Workbooks.Open(abs_path, ReadOnly=True)
        ws = _get_worksheet(wb, sheet)

        used = ws.UsedRange
        result = {
            "sheet": ws.Name,
            "path": abs_path,
            "used_range": used.Address,
            "rows": used.Rows.Count,
            "columns": used.Columns.Count,
            "first_row": used.Row,
            "first_column": used.Column,
        }

        wb.Close(SaveChanges=False)
        return result

    except (WorkbookNotFoundError, SheetNotFoundError):
        raise
    except Exception as exc:
        raise ExcelError(f"Failed to get range info: {exc}", context={"path": abs_path})
    finally:
        try:
            excel.Quit()
        except Exception:
            pass
