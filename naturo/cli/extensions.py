"""Windows-specific CLI extensions: excel."""
from __future__ import annotations

from typing import Any

import click
from naturo.cli.fuzzy_group import FuzzyGroup


# ── excel ───────────────────────────────────────


@click.group(hidden=True, cls=FuzzyGroup)
def excel() -> None:
    """Excel COM automation (Windows-specific).

    Automate Excel workbooks via COM interface — read/write cells, run macros,
    list sheets, and inspect used ranges.

    Requires Microsoft Excel and pywin32 (pip install pywin32).
    """
    pass


@excel.command("open")
@click.argument("path", type=click.Path())
@click.option("--visible", is_flag=True, help="Show Excel window")
@click.option("--read-only", is_flag=True, help="Open in read-only mode")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def excel_open_cmd(path, visible, read_only, json_output) -> None:
    """Open an Excel workbook and show its info.

    PATH is the workbook file (.xlsx, .xls, .xlsm).

    \b
    Examples:

      naturo excel open report.xlsx

      naturo excel open "C:\\Data\\sales.xlsx" --visible --json
    """
    import json as json_module
    from naturo.cli.error_helpers import emit_exception_error

    try:
        from naturo.excel import excel_open
        result = excel_open(path, visible=visible, read_only=read_only)
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="EXCEL_ERROR")
        return

    if json_output:
        click.echo(json_module.dumps({"success": True, **result}))
    else:
        click.echo(f"Opened: {result['path']}")
        click.echo(f"Sheets ({result['sheet_count']}): {', '.join(result['sheets'])}")
        click.echo(f"Active: {result['active_sheet']}")


@excel.command()
@click.argument("path", type=click.Path())
@click.argument("cell")
@click.option("--sheet", help="Sheet name (default: active sheet)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def read(path, cell, sheet, json_output) -> None:
    """Read a cell or range value from a workbook.

    PATH is the workbook file. CELL is a cell reference (A1) or range (A1:C10).

    \b
    Examples:

      naturo excel read report.xlsx A1

      naturo excel read data.xlsx "A1:D100" --sheet "Sales" --json
    """
    import json as json_module
    from naturo.cli.error_helpers import emit_exception_error

    try:
        from naturo.excel import excel_read
        result = excel_read(path, cell, sheet=sheet)
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="EXCEL_ERROR")
        return

    if json_output:
        click.echo(json_module.dumps({"success": True, **result}))
    else:
        value = result["value"]
        if isinstance(value, list):
            # Range result — format as table
            for row in value:
                click.echo("\t".join(str(c) if c is not None else "" for c in row))
        else:
            click.echo(f"{result['cell']} ({result['sheet']}): {value}")


@excel.command()
@click.argument("path", type=click.Path())
@click.argument("cell")
@click.argument("value")
@click.option("--sheet", help="Sheet name (default: active sheet)")
@click.option("--create", is_flag=True, help="Create workbook if it doesn't exist")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def write(path: str, cell: str, value: str, sheet: str | None, create: bool, json_output: bool) -> None:
    """Write a value to a cell in a workbook.

    PATH is the workbook file. CELL is the target cell (e.g., A1).
    VALUE is the data to write.

    \b
    Examples:

      naturo excel write report.xlsx A1 "Hello World"

      naturo excel write data.xlsx B2 42 --sheet "Numbers" --json
    """
    import json as json_module
    from naturo.cli.error_helpers import emit_exception_error

    # Try to convert numeric values
    write_value: Any = value
    try:
        write_value = int(value)
    except ValueError:
        try:
            write_value = float(value)
        except ValueError:
            pass

    try:
        from naturo.excel import excel_write
        result = excel_write(path, cell, write_value, sheet=sheet, create=create)
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="EXCEL_ERROR")
        return

    if json_output:
        click.echo(json_module.dumps({"success": True, **result}))
    else:
        click.echo(f"Wrote to {result['cell']} ({result['sheet']}): {write_value}")


@excel.command("list-sheets")
@click.argument("path", type=click.Path())
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def list_sheets(path, json_output) -> None:
    """List all sheets in a workbook.

    \b
    Examples:

      naturo excel list-sheets report.xlsx

      naturo excel list-sheets data.xlsx --json
    """
    import json as json_module
    from naturo.cli.error_helpers import emit_exception_error

    try:
        from naturo.excel import excel_list_sheets
        result = excel_list_sheets(path)
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="EXCEL_ERROR")
        return

    if json_output:
        click.echo(json_module.dumps({"success": True, **result}))
    else:
        click.echo(f"Workbook: {result['path']}")
        for i, name in enumerate(result["sheets"], 1):
            active = " (active)" if name == result["active_sheet"] else ""
            click.echo(f"  {i}. {name}{active}")


@excel.command("run-macro")
@click.argument("path", type=click.Path())
@click.argument("macro_name")
@click.option("--arg", "macro_args", multiple=True, help="Macro argument (repeatable)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def run_macro(path, macro_name, macro_args, json_output) -> None:
    """Run a VBA macro in a workbook.

    PATH is the workbook file (.xlsm). MACRO_NAME is the macro to run.

    \b
    Examples:

      naturo excel run-macro report.xlsm "Module1.FormatReport"

      naturo excel run-macro data.xlsm "UpdateData" --arg "2024" --arg "Q1" --json
    """
    import json as json_module
    from naturo.cli.error_helpers import emit_exception_error

    try:
        from naturo.excel import excel_run_macro
        result = excel_run_macro(path, macro_name, args=list(macro_args) or None)
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="EXCEL_ERROR")
        return

    if json_output:
        click.echo(json_module.dumps({"success": True, **result}))
    else:
        click.echo(f"Macro '{result['macro']}' executed.")
        if result.get("result") is not None:
            click.echo(f"Result: {result['result']}")


@excel.command("info")
@click.argument("path", type=click.Path())
@click.option("--sheet", help="Sheet name (default: active sheet)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def excel_info(path, sheet, json_output) -> None:
    """Get used range info for a worksheet.

    Shows the dimensions of the data area in the sheet.

    \b
    Examples:

      naturo excel info report.xlsx

      naturo excel info data.xlsx --sheet "Sales" --json
    """
    import json as json_module
    from naturo.cli.error_helpers import emit_exception_error

    try:
        from naturo.excel import excel_get_range_info
        result = excel_get_range_info(path, sheet=sheet)
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="EXCEL_ERROR")
        return

    if json_output:
        click.echo(json_module.dumps({"success": True, **result}))
    else:
        click.echo(f"Sheet: {result['sheet']}")
        click.echo(f"Used range: {result['used_range']}")
        click.echo(f"Rows: {result['rows']}, Columns: {result['columns']}")
