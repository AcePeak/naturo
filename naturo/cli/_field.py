"""Scriptable ``--field`` projection for list-style commands (#1206).

Common scripting lookups ("get the HWND of the SolidWorks main window") used to
force a pipe into ``jq``/Python because ``-j`` emits the whole row schema. A
``--field NAME[,NAME...]`` selector lets the value come straight out of naturo:

* text mode prints only the selected columns, one row per line, tab-separated in
  the order requested — so a single field of a single row is a **bare value**,
  capturable directly with ``HWND=$(naturo list windows --app X --field hwnd)``;
* ``-j`` still returns the canonical collection success envelope, but with each
  item projected down to exactly the requested fields.

Field names are validated against the command's row schema up front: an unknown
name fails loudly (``INVALID_INPUT``, listing the valid fields) instead of
silently emitting blank columns.
"""
from __future__ import annotations

from typing import Any, Sequence, TypeVar

import click

from naturo.cli._jsonio import json_dumps
from naturo.cli.error_helpers import emit_error, success_envelope

_CommandT = TypeVar("_CommandT")

_FIELD_HELP = (
    "Print only these columns (comma-separated for multiple, e.g. "
    "--field title,pid). Output is one row per line, tab-separated; a single "
    "field of a single row prints the bare value for $(...) capture."
)


def field_option(func: _CommandT) -> _CommandT:
    """Attach the shared ``-F/--field`` option to a Click command."""
    return click.option("-F", "--field", "field", default=None, help=_FIELD_HELP)(func)  # type: ignore[return-value]


def parse_fields(field: str | None) -> list[str] | None:
    """Parse a ``--field`` spec into an ordered list of names, or ``None``.

    ``None`` (the option was not given) is returned unchanged so callers can
    branch on "no projection requested". A provided spec is split on commas and
    stripped; empty tokens are dropped (an all-empty spec yields ``[]``, which
    :func:`resolve_fields` rejects as INVALID_INPUT).
    """
    if field is None:
        return None
    return [name.strip() for name in field.split(",") if name.strip()]


def format_value(value: Any) -> str:
    """Render a single projected cell for text output (``None`` -> empty)."""
    if value is None:
        return ""
    return str(value)


def resolve_fields(
    fields: list[str],
    valid_fields: Sequence[str],
    json_output: bool,
) -> None:
    """Validate requested ``fields`` against the row schema, or exit loudly.

    Emits an ``INVALID_INPUT`` error (JSON envelope or ``Error:`` line) and
    exits when no field is given or when any requested name is not a column, so
    a typo surfaces immediately instead of producing blank output.
    """
    if not fields:
        emit_error(
            "INVALID_INPUT",
            f"Specify at least one --field name. Valid fields: {', '.join(valid_fields)}",
            json_output,
        )
    unknown = [f for f in fields if f not in valid_fields]
    if unknown:
        emit_error(
            "INVALID_INPUT",
            f"Unknown --field name(s): {', '.join(unknown)}. "
            f"Valid fields: {', '.join(valid_fields)}",
            json_output,
        )


def emit_projection(
    rows: Sequence[dict[str, Any]],
    fields: list[str],
    collection_key: str,
    json_output: bool,
) -> None:
    """Emit the projected collection (call after :func:`resolve_fields`).

    Under ``-j`` returns the canonical success envelope with each item reduced
    to the requested fields; in text mode prints one row per line, the fields
    tab-separated in requested order.
    """
    if json_output:
        projected = [{f: row.get(f) for f in fields} for row in rows]
        click.echo(json_dumps(success_envelope(collection_key, projected), indent=2))
    else:
        for row in rows:
            click.echo("\t".join(format_value(row.get(f)) for f in fields))
