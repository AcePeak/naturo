"""Run the competitive coverage benchmark and emit the matrix (D1).

Usage::

    python -m benchmarks.competitive.run_competitive              # human table
    python -m benchmarks.competitive.run_competitive --markdown   # docs matrix
    python -m benchmarks.competitive.run_competitive --json       # raw data

Runs naturo vs the installed OSS rivals (``pywinauto``, ``pyautogui``) against
the **same** live windows, reusing the reproducible fixtures from
``benchmarks/recognition/`` (Chromium, real Electron, real Java/Swing, Excel via
COM) plus a UIA-native control (Notepad) so the matrix also shows the cases a
UIA-only rival *does* handle — honest, not cherry-picked.

Requires a real interactive Windows desktop and the rivals installed
(``pip install naturo[competitive]``). Frameworks/rivals that cannot run on the
host are recorded ``blocked: needs env`` rather than fabricated. The pure matrix
rendering it calls (``matrix.format_matrix_markdown``) is what the Linux CI test
pins; this runner is the Windows-only driver that feeds it real numbers.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Dict, List, Tuple

from benchmarks.competitive.harness import (
    PyAutoGUIAdapter,
    PywinautoAdapter,
    measure_competitive,
)
from benchmarks.competitive.matrix import (
    CompetitiveResult,
    build_matrix,
    format_matrix_markdown,
)


def collect_results() -> Tuple[List[CompetitiveResult], Dict[str, str]]:
    """Run every available head-to-head measurement on this desktop.

    Returns:
        ``(results, blocked_rivals)`` where ``results`` is the measured matrix
        rows and ``blocked_rivals`` maps a rival name to why it could not run
        here (rendered ``blocked: needs env``).
    """
    # Reuse the reproducible fixture apps from the recognition benchmark so both
    # benchmarks exercise the identical, owned windows.
    from benchmarks.recognition.harness import (
        ChromiumFixtureApp,
        ElectronFixtureApp,
        ExcelComFixtureApp,
        JavaSwingFixtureApp,
    )

    results: List[CompetitiveResult] = []

    # UIA-native app: a case pywinauto *should* pass too (honesty — rivals are
    # not zero everywhere; the moat is the non-UIA frameworks).
    notepad = measure_competitive(
        app="Notepad (UIA-native)",
        framework="UIA",
        window_title="Notepad",
    )
    if notepad.counts.get("pywinauto") is not None:
        results.append(notepad)

    for fixture_cls, framework in (
        (ChromiumFixtureApp, "Electron/CDP (Chromium web content)"),
        (ElectronFixtureApp, "Electron/CDP (real Electron)"),
        (JavaSwingFixtureApp, "Java Access Bridge"),
        (ExcelComFixtureApp, "Excel COM"),
    ):
        fixture = fixture_cls()
        if not fixture.available:
            continue
        with fixture:
            window = fixture.find_window()
            if window is None:
                continue
            results.append(
                measure_competitive(
                    app=_fixture_label(fixture),
                    framework=framework,
                    hwnd=window.hwnd,
                    pid=window.pid,
                )
            )

    # Ad-hoc real apps if open (documented, never fabricated).
    for spec in (
        {"app": "IntelliJ IDEA (Swing)", "framework": "Java Access Bridge",
         "title": "IntelliJ IDEA"},
        {"app": "Feishu / Lark (Electron)", "framework": "Electron/CDP",
         "title": "Feishu"},
    ):
        window = _find_window(spec["title"])
        if window is not None:
            results.append(
                measure_competitive(
                    app=spec["app"], framework=spec["framework"],
                    hwnd=window.hwnd, pid=window.pid,
                )
            )

    blocked_rivals: Dict[str, str] = {}
    if not PywinautoAdapter().available:
        blocked_rivals["pywinauto"] = "not installed on this host (Windows-only)."
    if not PyAutoGUIAdapter().available:
        blocked_rivals["pyautogui"] = "not installed on this host."
    return results, blocked_rivals


def _fixture_label(fixture) -> str:
    """A stable app label for a recognition fixture instance."""
    return type(fixture).__name__.replace("FixtureApp", "") + " fixture"


def _find_window(title_substring: str):
    """Find an open window by title substring, or ``None``."""
    from naturo.backends.base import get_backend

    for window in get_backend().list_windows():
        if title_substring in (window.title or ""):
            return window
    return None


def main(argv: List[str] | None = None) -> int:
    """CLI entry point. Exits 0 if naturo beat a rival on ≥1 framework."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true", help="emit raw JSON")
    group.add_argument("--markdown", action="store_true", help="emit the docs matrix")
    args = parser.parse_args(argv)

    results, blocked = collect_results()
    summary = build_matrix(results)

    if args.json:
        print(json.dumps(
            {"matrix": summary, "rows": [r.__dict__ for r in results],
             "blocked_rivals": blocked},
            indent=2, default=str,
        ))
    elif args.markdown:
        print(format_matrix_markdown(results, blocked_rivals=blocked))
    else:
        print(format_matrix_markdown(results, blocked_rivals=blocked))

    # Success = naturo proved superior on at least one framework from real runs.
    return 0 if summary["moat_frameworks"] else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
