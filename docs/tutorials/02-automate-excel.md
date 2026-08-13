# Tutorial 2 — Automate Excel with naturo

**What you'll build:** a small end-to-end flow that opens an Excel workbook,
lists its sheets, writes a few cells, reads a range back, and draws a chart from
the data — all through naturo's `excel` commands, which drive Excel over its COM
automation interface (no fragile screen-scraping, real cell values). By the end
you'll be reading and writing spreadsheet data programmatically and from Python.

> **Time:** ~10 minutes. **Platform:** Windows with Microsoft Excel installed.
> Excel automation needs `pywin32` (`pip install pywin32`) in addition to naturo.

## Prerequisites

```bash
pip install naturo pywin32
```

Verify:

```bash
naturo --version
```

Expected output:

```
naturo, version 0.3.2
```

> **Why COM, not the accessibility tree?** Excel's grid is custom-drawn — walking
> the UI tree gives you pixels, not values. naturo's `excel` commands talk to
> Excel through its COM object model, so you get the *actual* cell values,
> formulas, and ranges. This is naturo's Excel moat.

Throughout this tutorial we use `report.xlsx` as the workbook path; substitute
your own. Cell references are standard A1 notation (`A1`, `B2`, `A1:D100`).

---

## Step 1 — Create and open a workbook

If you don't have a workbook yet, the `write` command's `--create` flag will make
one on first write (Step 3). To open an existing workbook and inspect it:

```bash
naturo excel open report.xlsx
```

Expected output:

```
Opened: C:\...\report.xlsx
Sheets (1): Sheet1
Active: Sheet1
```

## Step 2 — List the sheets

```bash
naturo excel list-sheets report.xlsx
```

Expected output:

```
Workbook: C:\...\report.xlsx
  1. Sheet1 (active)
```

## Step 3 — Write cells

`naturo excel write <workbook> <cell> <value>` writes a single cell. Numeric
strings are converted to numbers automatically; text stays text. Use `--sheet`
to target a specific worksheet, and `--create` to create the workbook if it
doesn't exist yet.

```bash
# Header row
naturo excel write report.xlsx A1 "Month"   --create
naturo excel write report.xlsx B1 "Revenue"

# Data
naturo excel write report.xlsx A2 "Jan" --sheet Sheet1
naturo excel write report.xlsx B2 1200
naturo excel write report.xlsx A3 "Feb"
naturo excel write report.xlsx B3 1750
naturo excel write report.xlsx A4 "Mar"
naturo excel write report.xlsx B4 1500
```

Expected output for each write:

```
Wrote to B2 (Sheet1): 1200
```

## Step 4 — Read a cell or a range

Read one cell:

```bash
naturo excel read report.xlsx B2
```

Expected output:

```
B2 (Sheet1): 1200
```

Read a range — the result prints as tab-separated rows:

```bash
naturo excel read report.xlsx "A1:B4" --sheet Sheet1
```

Expected output:

```
Month	Revenue
Jan	1200
Feb	1750
Mar	1500
```

## Step 5 — Inspect the used range

`naturo excel info` reports the dimensions of the data area — handy before
reading a sheet whose size you don't know:

```bash
naturo excel info report.xlsx --sheet Sheet1
```

Expected output:

```
Sheet: Sheet1
Used range: A1:B4
Rows: 4, Columns: 2
```

## Step 6 — Create a chart from the data

`naturo excel create-chart` draws a chart from a source range. The `--range` is
required; `--type` is one of `bar`, `column`, `line`, `pie`, `area`, `scatter`
(default `column`). `--anchor` places the chart's top-left corner, and `--title`
sets its title.

```bash
naturo excel create-chart report.xlsx \
  --type column \
  --range "A1:B4" \
  --sheet Sheet1 \
  --title "Q1 Revenue" \
  --anchor D2
```

Expected output:

```
Created column chart 'Chart 1' on sheet Sheet1 from A1:B4
Anchor: D2
```

---

## The complete flow (CLI)

```bash
# 1. Write a header + three rows (create the workbook on first write)
naturo excel write report.xlsx A1 "Month"   --create
naturo excel write report.xlsx B1 "Revenue"
naturo excel write report.xlsx A2 "Jan"
naturo excel write report.xlsx B2 1200
naturo excel write report.xlsx A3 "Feb"
naturo excel write report.xlsx B3 1750
naturo excel write report.xlsx A4 "Mar"
naturo excel write report.xlsx B4 1500

# 2. Read it back
naturo excel read report.xlsx "A1:B4"

# 3. Inspect the used range
naturo excel info report.xlsx

# 4. Chart it
naturo excel create-chart report.xlsx --type column --range "A1:B4" \
  --title "Q1 Revenue" --anchor D2
```

Every command accepts `-j`/`--json` for machine-readable output — pipe it into
`jq` or a script when you're wiring this into a pipeline:

```bash
naturo excel read report.xlsx "A1:B4" --json
```

---

## The same flow in Python

The Excel operations live in the `naturo.excel` module — the exact functions the
CLI calls, so the Python path can't drift from the commands above. Import them
directly:

```python
from naturo.excel import (
    excel_write, excel_read, excel_get_range_info, excel_create_chart,
)

# Write a header + three data rows (create the workbook if missing).
excel_write("report.xlsx", "A1", "Month", create=True)
excel_write("report.xlsx", "B1", "Revenue")
for i, (month, rev) in enumerate([("Jan", 1200), ("Feb", 1750), ("Mar", 1500)], start=2):
    excel_write("report.xlsx", f"A{i}", month)
    excel_write("report.xlsx", f"B{i}", rev)

# Read the range back — returns a dict with a "value" that's a list of rows.
result = excel_read("report.xlsx", "A1:B4", sheet="Sheet1")
for row in result["value"]:
    print(row)

# Inspect the used range.
info = excel_get_range_info("report.xlsx", sheet="Sheet1")
print("Used range:", info["used_range"], "-", info["rows"], "rows")

# Chart it.
excel_create_chart("report.xlsx", "A1:B4", chart_type="column",
                   sheet="Sheet1", title="Q1 Revenue", anchor="D2")
```

Run it through naturo's runner so imports resolve cleanly:

```bash
naturo run excel_report.py
```

> **Macros:** if your workbook (`.xlsm`) has VBA, run a macro with
> `naturo excel run-macro report.xlsm "Module1.FormatReport"` — pass macro
> arguments with repeatable `--arg` flags.

---

## Next steps

- **Automate a native app first?** Start with
  [Tutorial 1 — Automate Notepad in 5 minutes](01-automate-notepad.md).
- **Build an AI agent** that reads/writes Excel through naturo's MCP tools:
  [Tutorial 3 — Build an AI agent with naturo](03-ai-agent-with-naturo.md).
- **Supported apps & adaptation** — [docs/SUPPORTED_APPS.md](../SUPPORTED_APPS.md).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `EXCEL_ERROR` / COM error on any command | Confirm Microsoft Excel is installed and `pip install pywin32` succeeded. |
| "Workbook not found" on `write`/`read` | Pass `--create` on the first `write` to create the file, or give the full path to an existing workbook. |
| Range read returns fewer rows than expected | Run `naturo excel info` first to see the true used range, then read that. |
| A cell you wrote shows as text, not a number | naturo converts numeric *strings* to numbers on write; pass the bare number (`1200`, not `"1200"`) if you want it numeric. |
