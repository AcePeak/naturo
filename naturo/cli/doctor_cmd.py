"""``naturo doctor`` — one-shot environment self-check (#898).

A first-time user, skeptical evaluator, or AI agent otherwise has to gather the
answer to "why doesn't naturo see anything?" through six separate probes —
session interactivity, optional dependencies, AI providers, primary-monitor DPI,
version, and data locations. ``naturo doctor`` runs all of them at once and
prints a single report; ``naturo doctor -j`` emits a structured envelope so
agents and CI can consume it the way ``kubectl cluster-info`` is consumed before
a deploy.

The command is strictly **read-only**: it reports gaps, never mutates state,
installs nothing, and makes no network call unless ``--check-updates`` is given.
Exit code follows the default ``see``/``click``/``type`` triad: ``0`` when both
required checks (interactive desktop session and the native core library) pass,
``1`` when either fails.
"""
from __future__ import annotations

import os
import platform
import sys
from dataclasses import dataclass
from typing import Optional

import click

from naturo.cli._jsonio import json_dumps
from naturo.cli.error_helpers import _RECOVERY_HINTS
from naturo.version import __version__

# ── Check status vocabulary (mirrors the error-envelope wording) ──────────────
STATUS_OK = "ok"
STATUS_WARN = "warn"
STATUS_FAIL = "fail"

_SESSION_HINT = _RECOVERY_HINTS.get("NO_DESKTOP_SESSION", (None, False))[0]

# Optional integrations probed by import. Each tuple is
# (import_name, human purpose, install hint).
_OPTIONAL_DEPS: tuple[tuple[str, str, str], ...] = (
    ("pyvda", "virtual desktops", "pip install naturo[desktop]"),
    ("mcp", "MCP server", "pip install naturo[mcp]"),
    ("PIL", "image annotate/crop (Pillow)", "pip install naturo[vision]"),
    ("win32api", "pywin32 Win32 bindings", "pip install pywin32"),
)

# Environment variables that, when set, supply an AI provider credential.
_PROVIDER_ENV_KEYS: tuple[str, ...] = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "OPENAI_API_KEY",
)


@dataclass
class Check:
    """A single diagnostic result.

    Attributes:
        name: Short human-readable label for the diagnostic.
        status: One of ``ok``, ``warn`` or ``fail``.
        detail: Machine-readable description of the finding.
        suggested_action: Optional recovery hint, consistent with the CLI's
            error envelopes; omitted from output when ``None``.
        required: Whether this check gates the process exit code. Not emitted in
            the output — only the desktop-session and native-core checks set it,
            mirroring the acceptance criterion for the default command triad.
    """

    name: str
    status: str
    detail: str
    suggested_action: Optional[str] = None
    required: bool = False

    def to_dict(self) -> dict[str, str]:
        """Render the check as an ordered envelope entry (drops ``required``)."""
        payload: dict[str, str] = {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
        }
        if self.suggested_action is not None:
            payload["suggested_action"] = self.suggested_action
        return payload


def _parse_version(value: str) -> tuple[int, ...]:
    """Parse a dotted version into a comparable tuple of leading integers.

    Non-numeric suffixes (e.g. ``"1.2.3rc1"``) are reduced to their leading
    integer so a best-effort ordering is always available without pulling in a
    parsing dependency.

    Args:
        value: A version string such as ``"0.3.1"``.

    Returns:
        A tuple of integers, e.g. ``(0, 3, 1)``; empty on a wholly unparseable
        input.
    """
    parts: list[int] = []
    for chunk in value.split("."):
        digits = ""
        for char in chunk:
            if char.isdigit():
                digits += char
            else:
                break
        if digits:
            parts.append(int(digits))
        else:
            break
    return tuple(parts)


def _fetch_latest_pypi_version(timeout: float = 3.0) -> Optional[str]:
    """Return naturo's latest released version on PyPI, or ``None`` on failure.

    Args:
        timeout: Socket timeout in seconds for the single HTTPS request.

    Returns:
        The version string from the PyPI JSON API, or ``None`` if the request
        fails for any reason (offline, proxy, DNS, malformed response).
    """
    import json
    import urllib.request

    try:
        request = urllib.request.Request(
            "https://pypi.org/pypi/naturo/json",
            headers={"User-Agent": f"naturo/{__version__} doctor"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        version = data.get("info", {}).get("version")
        return version if isinstance(version, str) and version else None
    except Exception:
        # Network/parse failures are non-fatal for a diagnostic; the caller
        # reports the gap as a warning rather than crashing the report.
        return None


def _check_version(check_updates: bool) -> Check:
    """Report the installed version and, on request, PyPI staleness."""
    if not check_updates:
        return Check(
            "naturo version",
            STATUS_OK,
            f"{__version__} (run with --check-updates to compare with PyPI)",
        )

    latest = _fetch_latest_pypi_version()
    if latest is None:
        return Check(
            "naturo version",
            STATUS_WARN,
            f"{__version__} (could not reach PyPI to check for updates)",
            suggested_action="Check network connectivity, then retry --check-updates.",
        )
    if _parse_version(latest) > _parse_version(__version__):
        return Check(
            "naturo version",
            STATUS_WARN,
            f"{__version__} (latest on PyPI: {latest})",
            suggested_action="pip install --upgrade naturo",
        )
    return Check(
        "naturo version",
        STATUS_OK,
        f"{__version__} (latest on PyPI: {latest} — up to date)",
    )


def _check_runtime() -> Check:
    """Report the Python interpreter and operating system."""
    return Check(
        "Runtime",
        STATUS_OK,
        f"Python {platform.python_version()} on {platform.platform()}",
    )


def _check_session() -> Check:
    """Report whether the current process has an interactive desktop session.

    This is a *required* check on Windows: without an interactive session the
    ``see``/``click``/``type`` triad cannot reach the desktop. On non-Windows
    platforms the desktop engine does not apply, so the check is informational.
    """
    if sys.platform != "win32":
        return Check(
            "Desktop session",
            STATUS_WARN,
            "not applicable on this platform (Windows-only desktop engine)",
        )
    try:
        from naturo.cli.interaction._common import _is_current_session_interactive

        interactive = _is_current_session_interactive()
    except Exception as exc:  # pragma: no cover - defensive, hard to trigger
        return Check(
            "Desktop session",
            STATUS_FAIL,
            f"session check raised an error: {exc}",
            suggested_action=_SESSION_HINT,
            required=True,
        )
    if interactive:
        return Check(
            "Desktop session",
            STATUS_OK,
            "interactive (UIA available)",
            required=True,
        )
    return Check(
        "Desktop session",
        STATUS_FAIL,
        "no interactive desktop session — naturo cannot see or drive the UI",
        suggested_action=_SESSION_HINT,
        required=True,
    )


def _check_core() -> Check:
    """Report whether the native core library loads and its version.

    Required on Windows: the default backends depend on ``naturo_core.dll``.
    """
    if sys.platform != "win32":
        return Check(
            "Native core",
            STATUS_WARN,
            "not applicable on this platform (Windows-only native engine)",
        )
    try:
        from naturo.bridge import NaturoCore

        version = NaturoCore().version()
        return Check(
            "Native core (naturo_core.dll)",
            STATUS_OK,
            f"loaded, version {version}",
            required=True,
        )
    except Exception as exc:
        return Check(
            "Native core (naturo_core.dll)",
            STATUS_FAIL,
            f"failed to load: {exc}",
            suggested_action="Reinstall the native library: pip install --force-reinstall naturo",
            required=True,
        )


def _check_primary_monitor() -> Check:
    """Report the primary monitor's resolution and DPI scaling."""
    if sys.platform != "win32":
        return Check(
            "Primary monitor",
            STATUS_WARN,
            "not applicable on this platform",
        )
    try:
        from naturo.backends.base import get_backend

        monitors = get_backend().list_monitors()
    except Exception as exc:
        return Check(
            "Primary monitor",
            STATUS_WARN,
            f"could not enumerate monitors: {exc}",
        )
    if not monitors:
        return Check("Primary monitor", STATUS_WARN, "no monitors detected")
    primary = next((m for m in monitors if m.is_primary), monitors[0])
    percent = int(round(primary.scale_factor * 100))
    return Check(
        "Primary monitor",
        STATUS_OK,
        f"{primary.width}x{primary.height} @ {percent}% scaling ({primary.dpi} dpi)",
    )


def _check_optional_deps() -> list[Check]:
    """Probe each optional integration by import and report availability."""
    import importlib

    checks: list[Check] = []
    for module_name, purpose, install_hint in _OPTIONAL_DEPS:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            checks.append(
                Check(
                    f"Optional dependency: {module_name}",
                    STATUS_WARN,
                    f"{purpose} — not installed",
                    suggested_action=install_hint,
                )
            )
            continue
        version = getattr(module, "__version__", None)
        detail = f"{purpose} — installed"
        if isinstance(version, str) and version:
            detail += f" ({version})"
        checks.append(Check(f"Optional dependency: {module_name}", STATUS_OK, detail))
    return checks


def _check_providers() -> Check:
    """Report configured AI providers (env keys + stored credentials)."""
    env_keys = [key for key in _PROVIDER_ENV_KEYS if os.environ.get(key)]
    try:
        from naturo.config import load_credentials

        stored_count = len(load_credentials())
    except Exception:
        stored_count = 0

    if env_keys or stored_count:
        parts: list[str] = []
        if env_keys:
            parts.append(f"env: {', '.join(env_keys)}")
        if stored_count:
            parts.append(f"{stored_count} stored provider(s)")
        return Check("AI providers", STATUS_OK, "; ".join(parts))
    return Check(
        "AI providers",
        STATUS_WARN,
        "no API key set and no stored credentials — AI features unavailable",
        suggested_action=(
            "Set ANTHROPIC_API_KEY or OPENAI_API_KEY, or run 'naturo config setup'."
        ),
    )


def _count_entries(path, want_dirs: bool) -> int:
    """Count direct child directories (or files) under ``path``; 0 if absent."""
    try:
        if not path.exists():
            return 0
        return sum(1 for child in path.iterdir() if child.is_dir() == want_dirs)
    except OSError:
        return 0


def _check_data_dirs() -> Check:
    """Report naturo's data locations and where logs are emitted."""
    from naturo.config import SNAPSHOTS_DIR

    home = SNAPSHOTS_DIR.parent
    snapshots = _count_entries(SNAPSHOTS_DIR, want_dirs=True)
    try:
        from naturo.recording import RECORDINGS_DIR

        recordings = _count_entries(RECORDINGS_DIR, want_dirs=False)
    except Exception:
        recordings = 0
    detail = (
        f"data dir {home} (snapshot sessions: {snapshots}, recordings: {recordings}); "
        "logs are written to stderr — raise verbosity with -v or --log-level"
    )
    return Check("Data locations", STATUS_OK, detail)


def _gather_checks(check_updates: bool) -> list[Check]:
    """Run every diagnostic and return the ordered list of results."""
    checks: list[Check] = [
        _check_version(check_updates),
        _check_runtime(),
        _check_session(),
        _check_core(),
        _check_primary_monitor(),
    ]
    checks.extend(_check_optional_deps())
    checks.append(_check_providers())
    checks.append(_check_data_dirs())
    return checks


_STATUS_GLYPH = {STATUS_OK: "✓", STATUS_WARN: "⚠", STATUS_FAIL: "✗"}
_STATUS_COLOR = {STATUS_OK: "green", STATUS_WARN: "yellow", STATUS_FAIL: "red"}


def _emit_human(checks: list[Check], success: bool) -> None:
    """Print the human-readable report to stdout/stderr."""
    # A failed required check is the headline a first-time user needs first.
    for check in checks:
        if check.required and check.status == STATUS_FAIL:
            click.secho(f"✗ {check.name}: {check.detail}", fg="red", bold=True, err=True)
    click.echo("naturo doctor — environment self-check\n")
    for check in checks:
        glyph = click.style(
            _STATUS_GLYPH.get(check.status, "?"), fg=_STATUS_COLOR.get(check.status)
        )
        # Pad the plain name (not the styled glyph) so columns line up whether
        # or not ANSI colour codes are emitted.
        click.echo(f"  {glyph} {check.name:<42} {check.detail}")
        if check.suggested_action and check.status != STATUS_OK:
            click.echo(f"      → {check.suggested_action}")
    click.echo("")
    if success:
        click.secho("All required checks passed.", fg="green")
    else:
        failed = sum(1 for c in checks if c.required and c.status == STATUS_FAIL)
        click.secho(
            f"{failed} required check(s) failed — see above.", fg="red", bold=True
        )


@click.command("doctor")
@click.option(
    "--check-updates",
    is_flag=True,
    help="Query PyPI to report whether a newer naturo release is available.",
)
@click.option("--json", "-j", "json_output", is_flag=True, help="JSON output")
@click.pass_context
def doctor(ctx, check_updates: bool, json_output: bool) -> None:
    """Run an environment self-check and print a single health report.

    Aggregates the session, native-core, dependency, AI-provider, monitor/DPI,
    version, and data-location diagnostics that otherwise take several separate
    commands to gather. Read-only — installs nothing and (without
    --check-updates) makes no network call.

    \b
    Examples:
      naturo doctor
      naturo doctor -j
      naturo doctor --check-updates
    """
    json_output = json_output or (ctx.obj or {}).get("json", False)

    checks = _gather_checks(check_updates)
    success = not any(c.status == STATUS_FAIL and c.required for c in checks)

    if json_output:
        payload = {
            "success": success,
            "checks": [c.to_dict() for c in checks],
            "count": len(checks),
        }
        click.echo(json_dumps(payload, indent=2))
    else:
        _emit_human(checks, success)

    sys.exit(0 if success else 1)
