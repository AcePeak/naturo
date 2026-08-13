"""Hermetic tests for :mod:`naturo.runtime.resolver`.

No network, no real embedded runtime, no desktop session: a fake ``python.exe``
is materialised under ``tmp_path`` and the interpreter/PATH probes are stubbed
with monkeypatch so the acceptance rule (prefer system, fall back to embedded)
is exercised deterministically on any platform.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from naturo.runtime import resolver
from naturo.runtime.resolver import (
    find_embedded_python,
    find_system_python,
    resolve_python,
)


def _make_embedded(base: Path, subpath: str = "_runtime/python/python.exe") -> Path:
    """Create a fake embedded ``python.exe`` under ``base`` and return its path."""
    exe = base / subpath
    exe.parent.mkdir(parents=True, exist_ok=True)
    exe.write_text("fake interpreter", encoding="utf-8")
    return exe


# --------------------------------------------------------------------------- #
# find_embedded_python — path construction
# --------------------------------------------------------------------------- #

def test_find_embedded_returns_none_when_absent(tmp_path: Path) -> None:
    assert find_embedded_python(tmp_path) is None


def test_find_embedded_locates_nested_runtime_layout(tmp_path: Path) -> None:
    exe = _make_embedded(tmp_path, "_runtime/python/python.exe")
    assert find_embedded_python(tmp_path) == str(exe)


def test_find_embedded_locates_dist_runtime_layout(tmp_path: Path) -> None:
    exe = _make_embedded(tmp_path, "dist/runtime/python/python.exe")
    assert find_embedded_python(tmp_path) == str(exe)


def test_find_embedded_locates_flat_layout(tmp_path: Path) -> None:
    exe = _make_embedded(tmp_path, "python.exe")
    assert find_embedded_python(tmp_path) == str(exe)


# --------------------------------------------------------------------------- #
# find_system_python — injected which/probe
# --------------------------------------------------------------------------- #

def test_find_system_python_selects_first_suitable() -> None:
    def which(name: str) -> str | None:
        return {"python": "/usr/bin/python"}.get(name)

    def probe(path: str) -> tuple[int, int] | None:
        return (3, 12)

    assert find_system_python(which=which, probe=probe) == "/usr/bin/python"


def test_find_system_python_rejects_too_old() -> None:
    def which(name: str) -> str | None:
        return f"/usr/bin/{name}"

    def probe(path: str) -> tuple[int, int] | None:
        return (3, 8)  # below MIN_PYTHON

    assert find_system_python(which=which, probe=probe) is None


def test_find_system_python_skips_missing_and_unprobeable() -> None:
    def which(name: str) -> str | None:
        # "python" is not on PATH; only "python3" resolves.
        return "/usr/bin/python3" if name == "python3" else None

    def probe(path: str) -> tuple[int, int] | None:
        return (3, 11)

    assert find_system_python(which=which, probe=probe) == "/usr/bin/python3"


def test_find_system_python_none_when_nothing_on_path() -> None:
    assert find_system_python(which=lambda name: None, probe=lambda path: (3, 12)) is None


# --------------------------------------------------------------------------- #
# resolve_python — the acceptance rule
# --------------------------------------------------------------------------- #

def test_prefers_system_when_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _make_embedded(tmp_path)  # embedded also available...
    monkeypatch.setattr(resolver, "find_system_python", lambda: "/usr/bin/python")
    # ...but system wins by default.
    assert resolve_python(base=tmp_path) == "/usr/bin/python"


def test_embedded_fallback_when_no_system(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    exe = _make_embedded(tmp_path)
    monkeypatch.setattr(resolver, "find_system_python", lambda: None)
    assert resolve_python(base=tmp_path) == str(exe)


def test_error_when_neither_available(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(resolver, "find_system_python", lambda: None)
    with pytest.raises(RuntimeError, match="No suitable Python runtime"):
        resolve_python(base=tmp_path)


def test_prefer_system_false_inverts_to_embedded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    exe = _make_embedded(tmp_path)
    monkeypatch.setattr(resolver, "find_system_python", lambda: "/usr/bin/python")
    # System is present, but prefer_system=False makes the embedded runtime win.
    assert resolve_python(prefer_system=False, base=tmp_path) == str(exe)


def test_prefer_system_false_falls_back_to_system(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # No embedded runtime staged; embedded-first still falls back to system.
    monkeypatch.setattr(resolver, "find_system_python", lambda: "/usr/bin/python")
    assert resolve_python(prefer_system=False, base=tmp_path) == "/usr/bin/python"
