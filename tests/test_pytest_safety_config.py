"""M4 criterion 3 — the default pytest config must keep injecting tests opt-in.

The ``ui``/``integration``/``desktop`` suites drive real ``SendInput`` / native
UIA against whatever window has focus. Without a default marker filter, an ad-hoc
or looped ``pytest <file>`` runs them and types into the user's active terminal
(this actually happened during M4 development). This guard asserts the default
``addopts`` deselects those markers so injecting tests only run under an explicit
``-m`` opt-in — enforcing the "cmd/terminals never touched" non-negotiable.

Pure text parse of ``pyproject.toml`` — no naturo import, no DLL — Linux-collectable.
"""
from __future__ import annotations

import re
from pathlib import Path

_PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def _addopts() -> str:
    text = _PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r"^addopts\s*=\s*(.+)$", text, re.MULTILINE)
    assert match, "pyproject.toml [tool.pytest.ini_options] must set a default addopts"
    return match.group(1)


def test_default_addopts_deselects_injecting_markers():
    """A bare ``pytest`` must not run real-desktop input/UIA tests by default."""
    addopts = _addopts()
    for marker in ("not ui", "not integration", "not desktop"):
        assert marker in addopts, (
            f"default addopts must deselect injecting tests — missing {marker!r}: {addopts}"
        )
