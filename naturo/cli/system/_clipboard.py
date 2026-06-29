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
import logging
import sys

import click

from naturo.cli.error_helpers import emit_error, emit_exception_error, json_error
from naturo.cli.fuzzy_group import FuzzyGroup

logger = logging.getLogger(__name__)


def _get_backend(json_output: bool = False):
    """Return the platform backend, raising UsageError if unavailable."""
    from naturo.backends.base import get_backend
    try:
        return get_backend()
    except Exception as exc:
        if json_output:
            click.echo(json_error("BACKEND_ERROR", str(exc)))
            sys.exit(1)
        raise click.UsageError(str(exc))


def _resolve_set_text(text: str | None, file_path: str | None, json_output: bool) -> str:
    """Resolve the clipboard-set payload from the chosen input source.

    Exactly one source must be supplied: the positional ``text``, a ``--file``
    path, or stdin (signalled by passing ``-`` as ``text``, the jq/sed
    convention). File and stdin sources sidestep the shell ARG_MAX limit that
    caps a positional argument and preserve real newlines verbatim.

    Args:
        text: The positional ``TEXT`` argument, ``-`` for stdin, or ``None``.
        file_path: Path supplied via ``--file``, or ``None``.
        json_output: Whether errors should be emitted as JSON.

    Returns:
        The resolved payload string to write to the clipboard.

    Raises:
        SystemExit: Via :func:`emit_error` when no source, multiple sources, or a
            missing/unreadable file is supplied. The process exits with code 1
            and a canonical ``INVALID_INPUT`` error envelope.
    """
    if file_path is not None and text is not None:
        emit_error(
            "INVALID_INPUT",
            "Provide the text either as the TEXT argument, via --file, or on "
            "stdin ('-') — not more than one source.",
            json_output,
        )

    if file_path is not None:
        import os
        if not os.path.exists(file_path):
            emit_error("INVALID_INPUT", f"File not found: {file_path}", json_output)
        try:
            with open(file_path, "r", encoding="utf-8") as handle:
                return handle.read()
        except OSError as exc:
            emit_error("INVALID_INPUT", f"Could not read file: {exc}", json_output)

    if text == "-":
        return sys.stdin.read()

    if text is None:
        emit_error(
            "INVALID_INPUT",
            "No text to set. Provide a TEXT argument, --file PATH, or '-' to "
            "read from stdin.",
            json_output,
        )

    return text


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

    Returns the text content of the system clipboard. When the clipboard holds
    non-text data (an image or a file-drop list) there is no text to return, so
    the reported ``format`` reflects the real content (``image``/``files``)
    rather than ``text``, and the plain output says the clipboard holds non-text
    data instead of falsely claiming it is empty (#1079). A genuinely empty
    clipboard reports ``format: empty``. ``clipboard info`` is the source of
    truth that ``get`` consults for this distinction.

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

    # Determine the real clipboard format so non-text content is never
    # misreported as empty text (#1079). When text is present the format is
    # unambiguously "text", so skip the extra clipboard probe; only consult
    # ``clipboard info`` when there is no text to tell a genuinely empty
    # clipboard apart from one holding an image or files. The ``--format``
    # choice (text-only) selects the read strategy, not the reported content
    # type, so it no longer dictates the ``format`` field.
    if text:
        clip_format = "text"
        has_text = True
    else:
        clip_format = "empty"
        has_text = False
        try:
            clip_info = backend.clipboard_info()
        except Exception as exc:
            # A failed info probe must not turn a successful (empty) read into
            # an error; fall back to reporting an empty clipboard.
            logger.debug("clipboard_info probe failed during get: %s", exc)
            clip_info = {}
        if isinstance(clip_info, dict):
            clip_format = clip_info.get("format") or "empty"
            has_text = bool(clip_info.get("has_text", False))

    if json_output:
        click.echo(json_dumps({
            "success": True,
            "action": "clipboard_get",
            "format": clip_format,
            "text": text,
            "length": len(text),
            "has_text": has_text,
        }))
    else:
        if text:
            click.echo(text)
        elif clip_format in ("image", "files"):
            click.echo(f"(clipboard contains non-text data: {clip_format})", err=True)
        else:
            click.echo("(clipboard is empty)", err=True)


@clipboard.command()
@click.argument("text", required=False)
@click.option("--file", "file_path", type=click.Path(),
              help="Read text from a file (mirrors 'naturo type --file')")
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
def set(text: str | None, file_path: str | None, json_output: bool) -> None:
    """Write text to the clipboard.

    Replaces the current clipboard content. The payload may come from a
    positional TEXT argument, from a file via --file, or from stdin by passing
    ``-`` as TEXT. --file and stdin avoid the shell ARG_MAX limit (~32 KB) that
    caps a positional argument, and preserve real newlines without shell-specific
    quoting. Exactly one source must be supplied.

    \b
    Examples:
        naturo clipboard set "hello world"      # Literal text
        naturo clipboard set --file notes.txt   # Read text from a file
        naturo see -j | naturo clipboard set -  # Read text from stdin
    """
    text = _resolve_set_text(text, file_path, json_output)

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
