"""Shared JSON serialization for CLI ``-j`` output.

Python's :func:`json.dumps` defaults to ``ensure_ascii=True``, which rewrites
every non-ASCII code point as a ``\\uXXXX`` escape. For naturo's machine-readable
``-j`` output that mangles human inspection of Chinese/Japanese/Korean window
titles, user-supplied paths, selector names and echoed error messages — and it
diverges from the non-JSON path, which already prints literal Unicode (#894).

:func:`json_dumps` is a thin wrapper that defaults ``ensure_ascii=False`` so all
CLI JSON emit sites produce literal UTF-8. The CLI entry point reconfigures
stdout/stderr to UTF-8 with ``errors="replace"`` (:mod:`naturo.cli`), so emitting
literal Unicode is safe on every platform and console. Output is byte-for-byte
identical to the stdlib default for pure-ASCII payloads, and remains valid JSON
that machine consumers decode to the same values either way.
"""
from __future__ import annotations

import json
from typing import Any


def json_dumps(obj: Any, **kwargs: Any) -> str:
    """Serialize ``obj`` to a JSON string, preserving literal non-ASCII text.

    A drop-in replacement for :func:`json.dumps` for CLI output: it defaults
    ``ensure_ascii`` to ``False`` so CJK and emoji round-trip literally instead
    of as ``\\uXXXX`` escapes. All other keyword arguments (``indent``,
    ``separators``, ``sort_keys``, ...) are forwarded unchanged, and an explicit
    ``ensure_ascii`` argument still takes precedence.

    Args:
        obj: The object to serialize.
        **kwargs: Keyword arguments forwarded to :func:`json.dumps`.

    Returns:
        The JSON-encoded string.
    """
    kwargs.setdefault("ensure_ascii", False)
    return json.dumps(obj, **kwargs)
