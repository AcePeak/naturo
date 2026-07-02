"""Optional dependency auto-installer for naturo.

Provides ``ensure_package`` and the ``@requires_package`` decorator to handle
missing optional dependencies gracefully — prompting the user to install them
interactively, or raising a clear error in non-interactive environments.
"""

from __future__ import annotations

import functools
import importlib
import logging
import subprocess
import sys
from typing import Callable, TypeVar

from naturo.errors import NaturoError

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)

# ---------------------------------------------------------------------------
# Installer detection
# ---------------------------------------------------------------------------

def _detect_installer() -> list[str]:
    """Detect the best pip-compatible installer for the current environment.

    Returns:
        Command prefix list, e.g. ``["uv", "pip", "install"]`` or
        ``[sys.executable, "-m", "pip", "install"]``.
    """
    # Check if we're in a pipx-managed environment
    try:
        import importlib.metadata as md
        dist = md.distribution("naturo")
        installer = (dist.read_text("INSTALLER") or "").strip().lower()
        if installer == "uv":
            return ["uv", "pip", "install"]
    except Exception as exc:
        logger.debug("Installer detection failed: %s", exc)

    # Default: use the current Python's pip
    return [sys.executable, "-m", "pip", "install"]


def _is_interactive() -> bool:
    """Return True if stdin is a TTY (interactive terminal)."""
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Core: ensure_package
# ---------------------------------------------------------------------------

def ensure_package(
    package: str,
    *,
    import_name: str | None = None,
    feature: str = "",
    install_extra: str | None = None,
    auto_install: bool | None = None,
    json_output: bool = False,
) -> None:
    """Ensure an optional package is importable, offering to install if missing.

    Args:
        package: PyPI package name (e.g. ``"pyvda"``).
        import_name: Python import name if different from *package*
            (e.g. ``"websocket"`` for the ``websocket-client`` package).
        feature: Human-readable feature description for prompts
            (e.g. ``"Virtual desktop"``).
        install_extra: If the package is available as a naturo extra, the
            extra name (e.g. ``"desktop"``).  Used only in the hint message.
        auto_install: Override interactive prompt.  ``True`` → install without
            asking; ``False`` → never prompt, just error; ``None`` (default) →
            prompt if TTY, error otherwise.
        json_output: When ``True``, the caller has requested machine-readable
            output, so this function must never prompt and never write prose to
            stdout (#869).  The interactive prompt is suppressed (treated as a
            decline) and any install progress is silenced, leaving the caller's
            structured envelope as the sole content on stdout.  This is gated on
            the explicit flag rather than ``_is_interactive`` because on Windows
            ``sys.stdin.isatty()`` returns ``True`` even for a DEVNULL-redirected
            child, so a TTY check alone cannot protect non-interactive agents.

    Raises:
        NaturoError: If the package is not installed and cannot be installed
            (user declined, non-interactive, or install failed).
    """
    mod_name = import_name or package

    try:
        importlib.import_module(mod_name)
        return  # already available
    except ImportError:
        pass

    # Build a user-friendly install hint
    hint = f"pip install {package}"
    if install_extra:
        hint = f"pip install naturo[{install_extra}]"

    feature_label = f"{feature} support" if feature else f"'{package}'"

    # Determine whether to prompt
    should_install = auto_install
    if should_install is None:
        if json_output:
            # JSON mode: never prompt — emit only the structured error envelope.
            should_install = False
        elif _is_interactive():
            try:
                answer = input(
                    f"\n  {feature_label} requires '{package}'.\n"
                    f"  Install it now? [Y/n]: "
                ).strip().lower()
                should_install = answer in ("", "y", "yes")
            except (EOFError, KeyboardInterrupt):
                should_install = False
                print()  # newline after ^C
        else:
            should_install = False

    if not should_install:
        raise NaturoError(
            message=f"{feature_label} requires '{package}'. Install: {hint}",
            code="MISSING_DEPENDENCY",
            category="setup",
            suggested_action=f"Run '{hint}' to enable this feature.",
        )

    # Attempt installation
    installer = _detect_installer()
    cmd = installer + [package]
    logger.info("Installing %s: %s", package, " ".join(cmd))

    try:
        if not json_output:
            print(f"\n  Installing {package}...", end=" ", flush=True)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            if not json_output:
                print("failed ❌")
            logger.error("pip install failed: %s", result.stderr[:500])
            raise NaturoError(
                message=f"Failed to install '{package}': {result.stderr[:200]}",
                code="INSTALL_FAILED",
                category="setup",
                suggested_action=f"Try manually: {hint}",
            )
        if not json_output:
            print("done ✅")
    except subprocess.TimeoutExpired:
        if not json_output:
            print("timed out ❌")
        raise NaturoError(
            message=f"Installation of '{package}' timed out after 120s",
            code="INSTALL_TIMEOUT",
            category="setup",
            suggested_action=f"Try manually: {hint}",
        )

    # Verify import works after install
    try:
        importlib.import_module(mod_name)
    except ImportError:
        raise NaturoError(
            message=f"Installed '{package}' but still cannot import '{mod_name}'",
            code="IMPORT_FAILED",
            category="setup",
            suggested_action=f"Try: {hint}",
        )


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------

def requires_package(
    package: str,
    *,
    import_name: str | None = None,
    feature: str = "",
    install_extra: str | None = None,
) -> Callable[[F], F]:
    """Decorator that ensures an optional package before running the function.

    Args:
        package: PyPI package name.
        import_name: Python import name if different.
        feature: Human-readable feature label.
        install_extra: Naturo extras group name.

    Returns:
        Decorator that wraps the function with ``ensure_package`` call.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Forward the command's JSON flag (if it has one) so the dependency
            # check honours machine-readable output and never prompts (#869).
            ensure_package(
                package,
                import_name=import_name,
                feature=feature,
                install_extra=install_extra,
                json_output=bool(kwargs.get("json_output", False)),
            )
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
