"""Regression guard for #1204: the test harness must not call ``platform.system()``.

`platform.system()` (via `platform.uname()` → `_syscmd_ver()`) shells out to
``cmd /c ver`` on Windows. In a headless / no-console session that subprocess can
**never return**, so any module-level `platform.system()` in `conftest.py` hangs
pytest at collection time — which silently degrades the local test gate (a Dev
cycle then can't run the full suite, so blast-radius misses ship Windows-green /
CI-red, e.g. #1203). Use the cheap constant ``os.name == "nt"`` instead.

This test fails if `conftest.py` ever reintroduces a `platform.system()` *call*,
keeping the harness hang-free. (Source/AST scan, not a runtime spawn — itself safe.)
"""
from __future__ import annotations

import ast
from pathlib import Path

CONFTEST = Path(__file__).parent / "conftest.py"


def _platform_system_calls(source: str) -> list[int]:
    """Line numbers of any `platform.system(...)` call expression in *source*."""
    tree = ast.parse(source)
    hits: list[int] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "system"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "platform"
        ):
            hits.append(node.lineno)
    return hits


def test_conftest_does_not_call_platform_system() -> None:
    hits = _platform_system_calls(CONFTEST.read_text(encoding="utf-8"))
    assert not hits, (
        "tests/conftest.py calls platform.system() at line(s) "
        f"{hits} — this spawns `cmd /c ver` and HANGS pytest in a headless "
        "session (#1204). Use `os.name == 'nt'` instead."
    )


def test_guard_detects_a_real_platform_system_call() -> None:
    """Positive control: the AST scanner actually catches the bad pattern."""
    bad = "import platform\nflag = platform.system() == 'Windows'\n"
    assert _platform_system_calls(bad) == [2]
