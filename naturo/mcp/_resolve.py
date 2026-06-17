"""Shared window-selector resolution for MCP tools (#957).

A recurring silent-failure bug class (#954/#956): an MCP tool accepts a window
selector (``window_title``/``hwnd``/``pid``), fails to resolve it, and silently
proceeds against the foreground window — returning ``success:true`` on the
wrong window. :func:`require_hwnd` is the single resolution path that closes
this class: a selector that is *provided but does not resolve* raises
:class:`~naturo.errors.WindowNotFoundError` (which the MCP layer maps to a
``success:false`` / ``WINDOW_NOT_FOUND`` envelope), and resolution *never*
falls back to the foreground window. When no selector is given, the documented
foreground default (HWND ``0``) is returned.
"""
from __future__ import annotations

from typing import Optional

from naturo.backends.base import Backend


def require_hwnd(
    backend: Backend,
    *,
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
    pid: Optional[int] = None,
) -> int:
    """Resolve a window selector to a concrete HWND, or fail loudly.

    Args:
        backend: The active platform backend.
        window_title: Target window title (partial match). ``None`` means no
            title selector was supplied.
        hwnd: Explicit window handle. When truthy it is returned as-is and takes
            priority over ``window_title``/``pid``.
        pid: Target process ID. ``None`` means no PID selector was supplied.

    Returns:
        The resolved window handle, or ``0`` for the foreground window when no
        selector was supplied.

    Raises:
        WindowNotFoundError: When a selector (``window_title``/``pid``) is
            supplied but matches no window. The error is never swallowed and the
            foreground window is never used as a fallback, so the caller fails
            loudly instead of acting on the wrong window.
    """
    if hwnd:
        return hwnd
    if window_title is None and pid is None:
        return 0  # documented foreground default

    resolve = getattr(backend, "_resolve_hwnd", None)
    if resolve is None:
        # Backends without title/pid resolution (e.g. non-Windows) cannot honour
        # the selector; fall back to the foreground default rather than crash.
        return 0

    # Pass only the selectors that were actually supplied so the call mirrors
    # the historical single-kwarg invocation and an unmatched selector raises
    # WindowNotFoundError instead of resolving to the foreground window.
    kwargs: dict = {}
    if window_title is not None:
        kwargs["window_title"] = window_title
    if pid is not None:
        kwargs["pid"] = pid
    return resolve(**kwargs)
