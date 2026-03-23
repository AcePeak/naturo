"""Windows-specific extensions: excel, java, sap."""
import json as json_module
import sys

import click
from naturo.cli.fuzzy_group import FuzzyGroup


def _not_implemented(name: str, phase: str, json_output: bool) -> None:
    """Emit a NOT_IMPLEMENTED error with correct exit code.

    Args:
        name: Command name for the error message.
        phase: Phase identifier (e.g., '5C.1').
        json_output: Whether to emit JSON output.
    """
    msg = f"{name} is not implemented yet — coming in Phase {phase}"
    if json_output:
        click.echo(json_module.dumps({
            "success": False,
            "error": {"code": "NOT_IMPLEMENTED", "message": msg},
        }))
    else:
        click.echo(f"Error: {msg}", err=True)
    sys.exit(1)


# ── excel ───────────────────────────────────────


@click.group(hidden=True, cls=FuzzyGroup)
def excel():
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
def excel_open_cmd(path, visible, read_only, json_output):
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
def read(path, cell, sheet, json_output):
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
def write(path, cell, value, sheet, create, json_output):
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
def list_sheets(path, json_output):
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
def run_macro(path, macro_name, macro_args, json_output):
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
def excel_info(path, sheet, json_output):
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


# ── java ────────────────────────────────────────


@click.group(cls=FuzzyGroup)
def java():
    """Java application automation via Java Access Bridge (Windows-specific).

    Automate Java Swing/AWT applications using the Java Access Bridge API.
    """
    pass


@java.command(name="list")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def java_list(json_output):
    """List Java applications with Access Bridge enabled."""
    _not_implemented("java list", "5B.3", json_output)


@java.command()
@click.option("--pid", type=int, help="Java process ID")
@click.option("--title", help="Window title")
@click.option("--depth", type=int, default=5, help="Tree depth")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def tree(pid, title, depth, json_output):
    """Inspect Java UI element tree."""
    _not_implemented("java tree", "5B.3", json_output)


@java.command(name="click")
@click.argument("query")
@click.option("--pid", type=int, help="Java process ID")
@click.option("--title", help="Window title")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def java_click(query, pid, title, json_output):
    """Click a Java UI element."""
    _not_implemented("java click", "5B.3", json_output)


# ── sap ─────────────────────────────────────────


@click.group(cls=FuzzyGroup)
def sap():
    """SAP GUI Scripting automation (Windows-specific).

    Automate SAP GUI for Windows using the SAP Scripting API.
    """
    pass


@sap.command(name="list")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def sap_list(json_output):
    """List SAP GUI sessions."""
    _not_implemented("sap list", "5B.4", json_output)


@sap.command()
@click.argument("transaction")
@click.option("--session", type=int, default=0, help="Session index")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def run(transaction, session, json_output):
    """Run a SAP transaction code."""
    _not_implemented("sap run", "5B.4", json_output)


@sap.command(name="get")
@click.argument("field_id")
@click.option("--session", type=int, default=0, help="Session index")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def sap_get(field_id, session, json_output):
    """Get a SAP GUI field value."""
    _not_implemented("sap get", "5B.4", json_output)


@sap.command(name="set")
@click.argument("field_id")
@click.argument("value")
@click.option("--session", type=int, default=0, help="Session index")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def sap_set(field_id, value, session, json_output):
    """Set a SAP GUI field value."""
    _not_implemented("sap set", "5B.4", json_output)


# ── registry ────────────────────────────────────
