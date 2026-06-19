"""Shared helpers for core CLI commands.

Contains utility functions used across multiple core command modules
(capture, see, find, list, etc.).  Command submodules access these via::

    import naturo.cli.core._common as _common

This gives a single consistent mock-patch path:
``naturo.cli.core._common.<name>``.
"""
from __future__ import annotations

import errno
import functools
import json as json_module  # noqa: F401 — re-exported for submodules
import logging
import os
import platform
import sys
from collections.abc import Callable
from typing import TypeVar

import click

from naturo.cli.error_helpers import json_error as _json_error_str  # noqa: F401
from naturo.cli.fuzzy_group import FuzzyGroup  # noqa: F401
from naturo.errors import WindowNotFoundError  # noqa: F401

logger = logging.getLogger(__name__)

_F = TypeVar("_F", bound=Callable[..., object])


def require_desktop_session(json_output: bool = False) -> Callable[[_F], _F]:
    """Guard a CLI command so it refuses to run without a desktop session.

    Many enumeration/read commands (``app windows``, ``dialog detect``,
    ``taskbar list``, ``tray list``, ``wait --gone``) reach the backend
    without going through :func:`_get_backend`, so they historically returned
    fabricated success (empty arrays, stale window lists) in a
    ``NO_DESKTOP_SESSION`` environment instead of failing loudly (#885).

    Applying this decorator runs the exact same pre-flight check used by
    ``see``/``capture``/``click`` *before* the command body executes, making
    wrong-data-on-no-session structurally impossible at the entrypoint rather
    than relying on a per-command convention.

    Args:
        json_output: When True, emit a JSON ``NO_DESKTOP_SESSION`` error
            envelope and exit with status 1.  When False, emit a clean
            ``Error: ...`` message and exit with status 1 (no Click
            ``Usage:`` banner — a missing desktop is a runtime failure, not a
            usage error; see #866).

    Returns:
        A decorator that wraps the target command function with the guard.

    Raises:
        SystemExit: With status 1 if no interactive desktop session is
            available.
    """
    def decorator(func: _F) -> _F:
        @functools.wraps(func)
        def wrapper(*args: object, **kwargs: object) -> object:
            _enforce_desktop_session(json_output)
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator


def _enforce_desktop_session(json_output: bool) -> None:
    """Run the desktop-session pre-flight check, failing loudly on miss.

    Args:
        json_output: When True, emit a JSON ``NO_DESKTOP_SESSION`` envelope;
            when False, emit a clean ``Error: ...`` message.  Either way the
            process exits with status 1 — never Click's exit-2 ``Usage:``
            banner, which is reserved for genuine argument errors (#866).

    Raises:
        SystemExit: With status 1 when no desktop session exists.
    """
    from naturo.cli.interaction import _check_desktop_session
    try:
        _check_desktop_session()
    except Exception as exc:
        if json_output:
            click.echo(_json_error_str("NO_DESKTOP_SESSION", str(exc)))
        else:
            # A missing desktop is a runtime/environment failure, not a usage
            # error: emit a clean message and exit 1, never Click's exit-2
            # ``Usage:`` banner (#866).
            click.echo(f"Error: {exc}", err=True)
        raise SystemExit(1)


def _get_backend(json_output: bool = False):
    """Get the platform-appropriate backend.

    Performs a pre-flight check for an interactive desktop session on Windows
    so that see/find/capture give the same clear error as click/type/press
    instead of a vague 'No window found' message.

    Args:
        json_output: When True, emit JSON-formatted error and sys.exit
            instead of raising an exception for NoDesktopSessionError.

    Returns:
        A Backend instance for the current platform.

    Raises:
        SystemExit: With status 1 if no interactive desktop session exists.
    """
    _enforce_desktop_session(json_output)
    from naturo.backends.base import get_backend
    return get_backend()


def _platform_supports_gui() -> bool:
    """Check if the current platform has a GUI automation backend.

    Returns:
        True if Windows or macOS with Peekaboo installed.
    """
    system = platform.system()
    if system == "Windows":
        return True
    if system == "Darwin":
        import shutil
        return shutil.which("peekaboo") is not None
    return False


def _is_windows_11_or_later() -> bool:
    """Return True when running on Windows 11 (build 22000) or later.

    Windows 11 replaced the classic Win32 taskbar and notification-area
    toolbars (``MSTaskListWClass`` and ``TrayNotifyWnd`` under
    ``Shell_TrayWnd``) with a XAML shell host. The legacy UI Automation
    enumeration that drives ``taskbar list`` / ``tray list`` therefore returns
    zero elements on Windows 11 even when the taskbar and tray are populated
    (#916). Callers use this to warn that an empty listing may be incomplete
    rather than genuinely empty.

    Returns:
        True only on Windows with an OS build number of 22000 or higher; False
        on Windows 10 and earlier, and on every non-Windows platform.
    """
    if platform.system() != "Windows":
        return False
    try:
        return sys.getwindowsversion().build >= 22000  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return False


def _win11_shell_enumeration_warning(surface: str) -> str:
    """Build the Windows 11 shell-enumeration warning for an empty read.

    Args:
        surface: Human-readable name of the surface being enumerated, e.g.
            ``"taskbar"`` or ``"system tray"``.

    Returns:
        A single-line English warning explaining that the empty result may be
        incomplete because Windows 11 renders the surface with a XAML shell
        host that the legacy Win32 enumeration cannot read (#916).
    """
    return (
        f"Windows 11 renders the {surface} with a XAML shell host that the "
        "legacy Win32 enumeration cannot read, so this empty result may be "
        "incomplete rather than genuinely empty."
    )


def _platform_error_msg(feature: str) -> str:
    """Build a user-friendly platform error message.

    Args:
        feature: Description of the feature (e.g. 'Screen capture').

    Returns:
        Error message string.
    """
    system = platform.system()
    if system == "Darwin":
        return (
            f"{feature} requires Peekaboo on macOS. "
            "Install it from https://github.com/AcePeak/peekaboo"
        )
    if system == "Linux":
        return f"{feature} is not yet supported on Linux. See https://github.com/AcePeak/naturo#platform-support"
    return f"{feature} is not supported on {system}."


# Stable, English-only reasons keyed by ``errno``. ``OSError.strerror`` is
# rendered by the OS in the system locale, so interpolating it leaks non-English
# text into naturo's English-only CLI/``-j`` contract on a localized Windows
# (#1031). Map the errno to a fixed phrase instead; the numeric errno is kept for
# diagnostics, but never the localized string.
_OSERROR_REASONS: dict[int, str] = {
    errno.ENOENT: "a path component is missing or is not a directory",
    errno.ENOTDIR: "a path component is not a directory",
    errno.EACCES: "permission denied",
    errno.EPERM: "operation not permitted",
    errno.EEXIST: "a file already exists at that path",
    errno.EROFS: "the filesystem is read-only",
    errno.ENOSPC: "no space left on the device",
    errno.ENAMETOOLONG: "the path is too long",
}


def _oserror_reason(exc: OSError) -> str:
    """Return a stable, English-only reason describing an :class:`OSError`.

    Avoids ``exc.strerror``, which the OS renders in the system locale and would
    otherwise leak non-English text into naturo's English-only error contract
    (#1031). Falls back to the numeric errno (still English) for codes that are
    not explicitly mapped.

    Args:
        exc: The ``OSError`` raised while creating the output directory.

    Returns:
        An ASCII/English-only phrase suitable for interpolating into a
        user-facing message.
    """
    if exc.errno in _OSERROR_REASONS:
        return f"{_OSERROR_REASONS[exc.errno]} (errno {exc.errno})"
    if exc.errno is not None:
        return f"OS error {exc.errno}"
    return "the directory could not be created"


def _ensure_output_dir(path: str, json_output: bool) -> None:
    """Ensure the parent directory of an output file path exists.

    Auto-creates the parent directory (and any missing ancestors) so that
    writing an image to a not-yet-existing folder succeeds, instead of letting
    the backend raise a raw ``FileNotFoundError`` that downstream code
    mislabels as a capture failure (issue #1022).

    Args:
        path: The output file path the caller is about to write to.
        json_output: Whether the caller emits JSON error envelopes; controls
            the format of the error reported on failure.

    Raises:
        SystemExit: With exit code 1 if the parent directory cannot be created
            (e.g. permission denied, or a file occupies the path). The emitted
            error is a clear ``INVALID_INPUT`` naming the directory rather than
            a raw OS errno.
    """
    parent = os.path.dirname(os.path.abspath(path))
    if not parent or os.path.isdir(parent):
        return
    try:
        os.makedirs(parent, exist_ok=True)
    except OSError as exc:
        reason = _oserror_reason(exc)
        msg = (
            f"Cannot create output directory '{parent}': {reason}. "
            "Choose a writable --path or create the directory first."
        )
        if json_output:
            click.echo(_json_error_str("INVALID_INPUT", msg))
        else:
            click.echo(f"Error: {msg}", err=True)
        raise SystemExit(1)
