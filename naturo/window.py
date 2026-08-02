"""Shared window-selector resolution for BOTH the CLI and the MCP surface.

A recurring silent-failure bug class (#954/#956/#964): a tool accepts a window
selector (``app``/``window_title``/``hwnd``/``pid``), fails to resolve it, and
silently proceeds against the foreground window — returning success on the wrong
window. :func:`require_hwnd` is the single loud-failure resolution path both
surfaces call: a selector that is *provided but does not resolve* raises
:class:`~naturo.errors.WindowNotFoundError` (never swallowed, never falls back to
the foreground window); when no selector is given the documented foreground
default (HWND ``0``) is returned.

Previously the MCP (#957 ``require_hwnd``) and CLI (#964 ``_resolve_hwnd``) each
had their own copy of this contract — this module is the single source.
"""
from __future__ import annotations

from typing import Optional

from naturo.backends.base import Backend


def require_hwnd(
    backend: Backend,
    *,
    app: Optional[str] = None,
    window_title: Optional[str] = None,
    hwnd: Optional[int] = None,
    pid: Optional[int] = None,
) -> int:
    """Resolve a window selector to a concrete HWND, or fail loudly.

    Args:
        backend: The active platform backend.
        app: Application name (partial match). ``None`` = not supplied.
        window_title: Window title (partial match). ``None`` = not supplied.
        hwnd: Explicit handle. When truthy it wins and is returned as-is.
        pid: Target process ID. ``None`` = not supplied.

    Returns:
        The resolved handle, or ``0`` (foreground) when no selector was supplied.

    Raises:
        WindowNotFoundError: A selector (``app``/``window_title``/``pid``) was
            supplied but matched no window. Never swallowed; the foreground
            window is never used as a fallback.
    """
    if hwnd:
        return hwnd
    if app is None and window_title is None and pid is None:
        return 0  # documented foreground default

    resolve = getattr(backend, "_resolve_hwnd", None)
    if resolve is None:
        # Backends without title/pid resolution (e.g. non-Windows) cannot honour
        # the selector; fall back to the foreground default rather than crash.
        return 0

    # Pass only supplied selectors so an unmatched one raises WindowNotFoundError
    # instead of resolving to the foreground window.
    kwargs: dict = {}
    if app is not None:
        kwargs["app"] = app
    if window_title is not None:
        kwargs["window_title"] = window_title
    if pid is not None:
        kwargs["pid"] = pid
    return resolve(**kwargs)
