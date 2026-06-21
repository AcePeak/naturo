"""Shared helpers for ``naturo app`` CLI subcommands."""
from naturo.cli._jsonio import json_dumps
import logging
import os
import re
import sys

import click

from naturo.cli.error_helpers import json_error as _json_error_str

logger = logging.getLogger(__name__)

_APP_ID_RE = re.compile(r"a\d+$")


def _match_windows(windows, name_lower):
    """Match windows by name, excluding the calling process and prioritizing process name.

    Returns a list of matching windows sorted so that process-name matches
    come before title-only matches.  The calling process (own PID and its
    parent, to cover the terminal hosting the command) is excluded so that
    ``naturo app switch feishu`` doesn't accidentally match the terminal
    whose title contains the typed command.

    Args:
        windows: Iterable of window info objects with ``.process_name``,
            ``.title``, and ``.pid`` attributes.
        name_lower: Lowercased search term.

    Returns:
        List of matching windows (process-name matches first, then
        title-only matches), excluding windows owned by this process.
    """
    own_pid = os.getpid()
    parent_pid = os.getppid()

    process_matches = []
    title_matches = []
    for w in windows:
        if w.pid in (own_pid, parent_pid):
            continue
        if name_lower in w.process_name.lower():
            process_matches.append(w)
        elif name_lower in w.title.lower():
            title_matches.append(w)
    return process_matches + title_matches


def _safe_echo(text: str, **kwargs) -> None:
    """Echo text safely, replacing unencodable characters on Windows GBK terminals."""
    try:
        click.echo(text, **kwargs)
    except UnicodeEncodeError:
        # Fallback: encode with replace for terminals that can't handle the chars
        encoded = text.encode(sys.stdout.encoding or "utf-8", errors="replace")
        click.echo(encoded.decode(sys.stdout.encoding or "utf-8", errors="replace"), **kwargs)


def _resolve_app_id(name, json_output):
    """If *name* is an app ID (``a1``, ``a2``, …), resolve it via the session map.

    Args:
        name: Potential app ID string (positional NAME or ``--app`` value).
        json_output: Whether to emit JSON error output.

    Returns:
        The :class:`~naturo.app_ids.AppIdEntry` when the ID resolves
        successfully, ``False`` when the ID pattern matched but the entry
        is expired or unknown (error already emitted), or ``None`` when
        *name* does not match the ``a<N>`` pattern at all.
    """
    if name is None or not _APP_ID_RE.fullmatch(name):
        return None

    from naturo.app_ids import get_app_id_map

    entry = get_app_id_map().resolve(name)
    if entry is None:
        msg = f'App ID "{name}" not found or expired. Run "naturo app list" to refresh.'
        if json_output:
            click.echo(_json_error_str("APP_ID_NOT_FOUND", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        return False
    return entry


def _resolve_window_target(backend, name, window_title=None, hwnd=None, pid=None):
    """Build keyword arguments for backend window methods.

    Accepts the unified window-targeting flag set: positional NAME / ``--app``
    (*name*), ``--window`` (*window_title*), ``--hwnd``, and ``--pid``.

    Resolution dimensions (#1065 — consistent with the gold-standard
    ``see``/``capture``/``click`` and ``list windows``):

    * An explicit ``--hwnd`` always wins (most specific target).
    * Positional NAME / ``--app`` (*name*) and/or ``--pid`` are resolved to a
      concrete window handle through the backend's canonical ``_resolve_hwnd``
      resolver, which matches the **process name** first (title as a fallback)
      — the same path the gold-standard commands use.  This makes ``--app``
      mean "application/process name" everywhere, so it works for localized
      apps whose window title differs from the exe name (e.g. Calculator →
      ``计算器``).  *window_title* narrows the match when supplied alongside.
    * ``--window`` alone (*window_title* with no *name*/*pid*) keeps
      title-substring semantics — the backend window method resolves the title.

    Args:
        backend: Active backend instance (provides ``_resolve_hwnd``).
        name: Application/process name (positional NAME or ``--app``).
        window_title: Optional title substring to pick a specific window.
        hwnd: Optional direct window handle (takes priority over *name*/*pid*).
        pid: Optional process ID to target.

    Returns:
        Dict with ``title`` and/or ``hwnd`` keys for backend calls.

    Raises:
        WindowNotFoundError: When *name*/*pid* match no resolvable window
            (propagated from ``_resolve_hwnd``).
    """
    # Explicit --hwnd is the most specific target and short-circuits resolution.
    if hwnd is not None:
        return {"title": window_title or name, "hwnd": hwnd}
    # NAME/--app and/or --pid → canonical process-aware resolver (#1065): the
    # same path see/capture/click use, so --app means process name, not title.
    if (name is not None or pid is not None) and hasattr(backend, "_resolve_hwnd"):
        resolved_hwnd = backend._resolve_hwnd(app=name, window_title=window_title, pid=pid)
        return {"title": None, "hwnd": resolved_hwnd}
    # --window only (or a backend without _resolve_hwnd): title-substring match,
    # resolved by the backend method itself.
    return {"title": window_title or name, "hwnd": hwnd}


def _require_target(name, window_title, hwnd, pid, json_output):
    """Validate that at least one target identifier is provided.

    Returns:
        True if valid, False if error was emitted.
    """
    if not name and not window_title and not hwnd and not pid:
        msg = "Specify an app name, --window, --hwnd, or --pid"
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            _safe_echo(f"Error: {msg}", err=True)
        sys.exit(1)
        return False
    return True


def _handle_naturo_error(exc, json_output) -> None:
    """Emit a NaturoError and exit."""
    if json_output:
        click.echo(json_dumps(exc.to_json_response()))
    else:
        _safe_echo(f"Error: {exc.message}", err=True)
    sys.exit(1)


def _handle_generic_error(exc, json_output) -> None:
    """Emit a generic exception and exit."""
    if json_output:
        click.echo(_json_error_str("UNKNOWN_ERROR", str(exc)))
    else:
        _safe_echo(f"Error: {exc}", err=True)
    sys.exit(1)
