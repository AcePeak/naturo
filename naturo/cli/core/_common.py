"""Shared helpers for core CLI commands.

Contains utility functions used across multiple core command modules
(capture, see, find, list, etc.).  Command submodules access these via::

    import naturo.cli.core._common as _common

This gives a single consistent mock-patch path:
``naturo.cli.core._common.<name>``.
"""
from __future__ import annotations

import functools
import json as json_module  # noqa: F401 — re-exported for submodules
import logging
import platform
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
