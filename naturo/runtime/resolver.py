"""Locate the Python interpreter naturo should run under.

Naturo can be deployed two ways:

* as a normal ``pip install`` into a **system** Python, or
* as a self-contained bundle that ships an **embedded** CPython runtime
  (see ``scripts/bundle_python.py``) so the machine needs no pre-installed
  Python at all.

This module answers a single question — *which* ``python.exe`` should drive
naturo — and implements the acceptance rule for issue #41:

    Prefer a system Python when one is available; fall back to the bundled
    embedded runtime otherwise.

The logic is deliberately pure and filesystem-injectable (every entry point
accepts the lookup surface it depends on) so it can be unit-tested without a
real interpreter, a network, or a desktop session. Nothing here has import-time
side effects.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional, Sequence, Tuple

# Minimum interpreter naturo supports, mirroring ``requires-python = ">=3.9"``
# in pyproject.toml. A system Python older than this is treated as unusable.
MIN_PYTHON: Tuple[int, int] = (3, 9)

# Executable names to probe on PATH, in priority order.
_SYSTEM_CANDIDATES: Tuple[str, ...] = ("python", "python3")

# Locations (relative to a supplied ``base``) where an embedded runtime's
# ``python.exe`` may live. ``bundle_python.py`` writes to ``dist/runtime/python``
# during a build, while a shipped bundle nests the runtime beside the package as
# ``_runtime/python``. Both layouts (and a couple of flatter variants) are
# probed so the resolver works regardless of how the bundle was staged.
_EMBEDDED_SUBPATHS: Tuple[Path, ...] = (
    Path("_runtime") / "python" / "python.exe",
    Path("dist") / "runtime" / "python" / "python.exe",
    Path("runtime") / "python" / "python.exe",
    Path("python") / "python.exe",
    Path("python.exe"),
)

# Callable that returns the ``(major, minor)`` version of the interpreter at a
# path, or ``None`` if it cannot be determined. Injectable for tests.
VersionProbe = Callable[[str], Optional[Tuple[int, int]]]
# Callable that resolves an executable name to a full path (``shutil.which``).
PathLookup = Callable[[str], Optional[str]]


def _probe_version(executable: str) -> Optional[Tuple[int, int]]:
    """Return the ``(major, minor)`` version of ``executable``.

    Runs the interpreter with a tiny one-liner rather than trusting the file
    name, so an ambiguously named ``python`` is classified correctly. Any
    failure (missing binary, non-zero exit, unparseable output) yields
    ``None`` — the caller then treats the candidate as unusable.

    Args:
        executable: Path to a Python interpreter.

    Returns:
        The interpreter's ``(major, minor)`` version, or ``None``.
    """
    try:
        proc = subprocess.run(
            [executable, "-c", "import sys;print(sys.version_info[0], sys.version_info[1])"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    parts = proc.stdout.split()
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def find_system_python(
    min_version: Tuple[int, int] = MIN_PYTHON,
    *,
    candidates: Sequence[str] = _SYSTEM_CANDIDATES,
    which: PathLookup = shutil.which,
    probe: VersionProbe = _probe_version,
) -> Optional[str]:
    """Locate a suitable system Python on ``PATH``.

    Probes ``candidates`` in order, resolving each with ``which`` and checking
    its version with ``probe``. The first interpreter that is present and at
    least ``min_version`` wins.

    Args:
        min_version: Lowest acceptable ``(major, minor)`` version.
        candidates: Executable names to try, in priority order.
        which: Name-to-path resolver (defaults to :func:`shutil.which`).
        probe: Version probe (defaults to running the interpreter).

    Returns:
        The absolute path to a usable system Python, or ``None`` if none found.
    """
    for name in candidates:
        path = which(name)
        if not path:
            continue
        version = probe(path)
        if version is not None and version >= min_version:
            return path
    return None


def find_embedded_python(base: Path) -> Optional[str]:
    """Locate a bundled embedded ``python.exe`` under ``base``.

    Checks the known bundle layouts (see :data:`_EMBEDDED_SUBPATHS`) and returns
    the first ``python.exe`` that exists on disk. Purely a filesystem check — the
    interpreter is not executed here.

    Args:
        base: Directory the embedded runtime is staged relative to (typically
            the naturo package dir or a repo/dist root).

    Returns:
        The path to the embedded interpreter, or ``None`` if absent.
    """
    for sub in _EMBEDDED_SUBPATHS:
        candidate = base / sub
        if candidate.is_file():
            return str(candidate)
    return None


def _default_base() -> Path:
    """Return the default search base: the naturo package's parent directory.

    A shipped bundle stages the embedded runtime beside the installed package,
    so the package's parent is the natural anchor for :func:`find_embedded_python`.
    """
    return Path(__file__).resolve().parent.parent


def resolve_python(prefer_system: bool = True, base: Optional[Path] = None) -> str:
    """Resolve which Python interpreter naturo should run under.

    Implements issue #41's acceptance rule: **prefer a system Python, fall back
    to the embedded runtime**. Pass ``prefer_system=False`` to invert the order
    (embedded first) — useful when a caller wants the pinned, bundled runtime.

    Args:
        prefer_system: When ``True`` (default) a usable system Python wins; when
            ``False`` the embedded runtime is preferred.
        base: Directory to search for the embedded runtime. Defaults to the
            naturo package's parent directory.

    Returns:
        The path to the chosen interpreter.

    Raises:
        RuntimeError: If neither a system nor an embedded interpreter is found.
    """
    search_base = _default_base() if base is None else base
    system = find_system_python()
    embedded = find_embedded_python(search_base)

    order = (system, embedded) if prefer_system else (embedded, system)
    for chosen in order:
        if chosen is not None:
            return chosen

    raise RuntimeError(
        "No suitable Python runtime found: neither a system Python "
        f">= {MIN_PYTHON[0]}.{MIN_PYTHON[1]} on PATH nor a bundled embedded "
        f"runtime under {search_base}. Build one with scripts/bundle_python.py "
        "or install a supported Python."
    )
