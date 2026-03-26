"""Shared CLI table output utility (#357).

Provides a unified ``print_table`` function for consistent tabular output
across all ``naturo list`` and ``naturo app list`` commands.
"""
from __future__ import annotations

import json as json_module

import click


def print_table(
    headers: list[str],
    rows: list[list[str]],
    *,
    json_output: bool = False,
    json_key: str = "items",
    json_extra: dict | None = None,
    count_label: str | None = None,
) -> None:
    """Print a formatted table to stdout.

    In text mode, prints an aligned table with headers and a separator line.
    In JSON mode, emits ``{"success": true, <json_key>: [...], "count": N}``.

    Args:
        headers: Column header strings (e.g. ``["PID", "HWND", "TITLE"]``).
        rows: List of rows, each a list of cell values (strings).
        json_output: If True, emit JSON instead of text table.
        json_key: Top-level key for the list of items in JSON output.
        json_extra: Extra keys to merge into the JSON root dict.
        count_label: Optional label printed after the table
            (e.g. ``"3 applications"``).  When *None*, a default
            ``"{n} rows"`` line is printed.
    """
    if json_output:
        items = []
        for row in rows:
            item = {}
            for i, h in enumerate(headers):
                key = h.lower().replace(" ", "_")
                item[key] = row[i] if i < len(row) else ""
            items.append(item)
        out: dict = {"success": True, json_key: items, "count": len(items)}
        if json_extra:
            out.update(json_extra)
        click.echo(json_module.dumps(out, indent=2))
        return

    if not rows:
        click.echo("No items found.")
        return

    # Calculate column widths (minimum = header length)
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    # Print header
    header_line = "  ".join(
        h.ljust(col_widths[i]) for i, h in enumerate(headers)
    )
    click.echo(header_line)
    click.echo("-" * len(header_line))

    # Print rows
    for row in rows:
        line = "  ".join(
            str(row[i] if i < len(row) else "").ljust(col_widths[i])
            for i in range(len(headers))
        )
        click.echo(line)

    # Footer count
    if count_label is not None:
        click.echo(f"\n{count_label}")
    else:
        click.echo(f"\n{len(rows)} rows.")
