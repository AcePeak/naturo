"""Clipboard CLI commands — read, write, clear, and inspect clipboard contents.

Provides commands for clipboard data management, essential for AI agents
that need to transfer data between applications via the system clipboard.

Examples:
    naturo clipboard get                        # Read clipboard text
    naturo clipboard set "hello world"          # Write text to clipboard
    naturo clipboard clear                      # Clear clipboard
    naturo clipboard info                       # Show clipboard format and size
"""

from __future__ import annotations

from naturo.cli._jsonio import json_dumps
import sys

import click

from naturo.cli.error_helpers import emit_exception_error
from naturo.cli.fuzzy_group import FuzzyGroup


def _get_backend(json_output: bool = False):
    """Return the platform backend, raising UsageError if unavailable."""
    from naturo.backends.base import get_backend
    try:
        return get_backend()
    except Exception as exc:
        if json_output:
            click.echo(json_dumps({
                "success": False,
                "error": "BACKEND_ERROR",
                "message": str(exc),
            }))
            sys.exit(1)
        raise click.UsageError(str(exc))


@click.group(cls=FuzzyGroup)
def clipboard() -> None:
    """Read, write, and manage clipboard contents.

    Data management for the system clipboard. Supports reading and writing
    text content. AI agents use this to transfer data between applications.

    \b
    Examples:
        naturo clipboard get                    # Read clipboard text
        naturo clipboard set "hello world"      # Write text to clipboard
        naturo clipboard clear                  # Clear clipboard contents
        naturo clipboard info                   # Show format and size
    """
    pass


@clipboard.command()
@click.option("--format", "fmt", type=click.Choice(["text"]), default="text",
              help="Output format (currently only text supported)")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def get(fmt: str, json_output: bool) -> None:
    """Read current clipboard content.

    Returns the text content of the system clipboard. If the clipboard is
    empty or contains non-text data, returns an empty string.

    \b
    Examples:
        naturo clipboard get                    # Print clipboard text
        naturo clipboard get --json             # JSON output with metadata
    """
    backend = _get_backend(json_output)
    try:
        text = backend.clipboard_get()
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="CLIPBOARD_ERROR")
        return

    if json_output:
        click.echo(json_dumps({
            "success": True,
            "action": "clipboard_get",
            "format": fmt,
            "text": text,
            "length": len(text),
        }))
    else:
        if text:
            click.echo(text)
        else:
            click.echo("(clipboard is empty)", err=True)


@clipboard.command()
@click.argument("text")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def set(text: str, json_output: bool) -> None:
    """Write text to the clipboard.

    Replaces the current clipboard content with the specified text.

    \b
    Examples:
        naturo clipboard set "hello world"      # Set clipboard text
        naturo clipboard set "line1\\nline2"     # Multi-line text
    """
    backend = _get_backend(json_output)
    try:
        backend.clipboard_set(text)
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="CLIPBOARD_ERROR")
        return

    if json_output:
        click.echo(json_dumps({
            "success": True,
            "action": "clipboard_set",
            "length": len(text),
        }))
    else:
        click.echo(f"Clipboard set ({len(text)} chars)")


@clipboard.command()
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def clear(json_output: bool) -> None:
    """Clear the clipboard contents.

    Removes all data from the system clipboard.

    \b
    Examples:
        naturo clipboard clear                  # Clear clipboard
    """
    backend = _get_backend(json_output)
    try:
        backend.clipboard_clear()
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="CLIPBOARD_ERROR")
        return

    if json_output:
        click.echo(json_dumps({
            "success": True,
            "action": "clipboard_clear",
        }))
    else:
        click.echo("Clipboard cleared")


@clipboard.command()
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def info(json_output: bool) -> None:
    """Show information about current clipboard contents.

    Reports the clipboard data format, size, and which content types
    are available (text, image, files).

    \b
    Examples:
        naturo clipboard info                   # Show clipboard info
        naturo clipboard info --json            # JSON output
    """
    backend = _get_backend(json_output)
    try:
        clip_info = backend.clipboard_info()
    except Exception as exc:
        emit_exception_error(exc, json_output, fallback_code="CLIPBOARD_ERROR")
        return

    if json_output:
        click.echo(json_dumps({
            "success": True,
            "action": "clipboard_info",
            **clip_info,
        }))
    else:
        fmt = clip_info.get("format", "unknown")
        size = clip_info.get("size", 0)
        has_text = clip_info.get("has_text", False)
        has_image = clip_info.get("has_image", False)
        has_files = clip_info.get("has_files", False)

        click.echo(f"Format:    {fmt}")
        click.echo(f"Size:      {size} bytes")
        available = []
        if has_text:
            available.append("text")
        if has_image:
            available.append("image")
        if has_files:
            available.append("files")
        click.echo(f"Available: {', '.join(available) if available else 'none'}")
