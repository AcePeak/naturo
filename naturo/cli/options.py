"""Shared CLI option decorators for consistent parameter naming.

Defines reusable Click option decorators so every command uses the same
parameter names, Python variable names, and help text.  Old aliases
(``--window-title``, ``--process-name``, ``--window-id``) are kept as
hidden options for backward compatibility but excluded from ``--help``.

Usage::

    from naturo.cli.options import app_option, window_option, hwnd_option, pid_option

    @click.command()
    @app_option
    @window_option
    @hwnd_option
    @pid_option
    def my_cmd(app, window, hwnd, pid, ...):
        ...
"""
from __future__ import annotations

import click


# ── Primary options (visible in --help) ──────────────────────────────────────

def app_option(func):
    """``--app`` — target application (partial name match)."""
    return click.option(
        "--app",
        default=None,
        help="Target application (name or partial match)",
    )(func)


def window_option(func):
    """``--window`` — window title pattern (substring match).

    Keeps ``--window-title`` and ``--title`` as hidden aliases.
    The Python parameter is always ``window``.
    """
    # Hidden aliases first so the primary ``--window`` wins in --help
    func = click.option(
        "--window-title", "window", default=None, hidden=True, help="",
    )(func)
    func = click.option(
        "--title", "window", default=None, hidden=True, help="",
    )(func)
    func = click.option(
        "--window", "window", default=None,
        help="Window title pattern (substring match)",
    )(func)
    return func


def hwnd_option(func):
    """``--hwnd`` — window handle (exact, for scripting).

    Keeps ``--window-id`` as a hidden alias.
    """
    func = click.option(
        "--window-id", "hwnd", default=None, type=int, hidden=True, help="",
    )(func)
    func = click.option(
        "--hwnd", default=None, type=int,
        help="Window handle (HWND)",
    )(func)
    return func


def pid_option(func):
    """``--pid`` — process ID (exact)."""
    return click.option(
        "--pid", default=None, type=int,
        help="Process ID",
    )(func)


def on_option(func):
    """``--on`` — target element ref (eN) or text label."""
    return click.option(
        "--on", "on_ref", default=None,
        help="Target element (eN ref or text label)",
    )(func)



def json_option(func):
    """``--json / -j`` — JSON output mode."""
    return click.option(
        "--json", "-j", "json_output", is_flag=True,
        help="JSON output",
    )(func)


# ── Hidden backward-compat aliases ──────────────────────────────────────────

def process_name_option(func):
    """Hidden ``--process-name`` alias for ``--app``.

    Maps to the same Python parameter ``app`` so existing scripts
    using ``--process-name`` continue to work.
    """
    return click.option(
        "--process-name", "app", default=None, hidden=True, help="",
    )(func)
