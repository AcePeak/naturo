"""Shared helpers for core CLI commands.

Contains utility functions used across multiple core command modules
(capture, see, find, list, etc.).  Command submodules access these via::

    import naturo.cli.core._common as _common

This gives a single consistent mock-patch path:
``naturo.cli.core._common.<name>``.
"""
from __future__ import annotations

import json as json_module  # noqa: F401 — re-exported for submodules
import logging
import platform

import click

from naturo.cli.error_helpers import json_error as _json_error_str  # noqa: F401
from naturo.cli.fuzzy_group import FuzzyGroup  # noqa: F401
from naturo.errors import WindowNotFoundError  # noqa: F401

logger = logging.getLogger(__name__)


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
        click.UsageError: If no interactive desktop session or no backend.
    """
    from naturo.cli.interaction import _check_desktop_session
    try:
        _check_desktop_session()
    except Exception as exc:
        if json_output:
            click.echo(_json_error_str("NO_DESKTOP_SESSION", str(exc)))
            raise SystemExit(1)
        raise click.UsageError(str(exc))
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
