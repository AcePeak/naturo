"""Run the recognition-coverage benchmark and print a reproducible table.

Usage::

    python -m benchmarks.recognition.run_benchmark            # human table
    python -m benchmarks.recognition.run_benchmark --json     # JSON output
    python -m benchmarks.recognition.run_benchmark --markdown # Markdown table

The benchmark runs two reproducible fixtures — the Chromium HTML fixture (the
Electron-class web-content case) and an owned, real Electron app (the literal
Electron case) — and additionally probes for a few common real apps (a
JetBrains IDE, DBeaver, Feishu) that may be open on the current desktop,
including them when present and documenting them as gaps when not.

Each row reports, on the *same* app:

* ``UIA-only`` — elements a UIA-only rival (Windows-MCP / Terminator / UFO²)
  would see.
* ``Cascade`` — elements naturo's full multi-framework cascade recognizes.
* ``Delta`` — the multi-framework advantage.
* ``Extra via`` — which provider found the extra elements.

This script requires a real interactive Windows desktop session and (for the
Chromium fixture) a Chrome/Edge install plus the ``cdp`` extra
(``pip install naturo[cdp]``).
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List

from benchmarks.recognition.harness import (
    ChromiumFixtureApp,
    CoverageResult,
    ElectronFixtureApp,
    JavaSwingFixtureApp,
    measure_running_app,
)

# Optional real apps to probe for on the current desktop.  Each is included in
# the report only if a matching window is currently open; otherwise it is
# recorded as a documented gap rather than fabricated.
OPTIONAL_APPS = [
    {
        "app": "JetBrains IDE (IntelliJ/PyCharm)",
        "framework": "Java Access Bridge",
        "title_substring": "IntelliJ IDEA",
    },
    {
        "app": "DBeaver",
        "framework": "Java Access Bridge (SWT)",
        "title_substring": "DBeaver",
    },
    {
        "app": "Feishu / Lark",
        "framework": "Electron/CDP",
        "title_substring": "Feishu",
    },
]


def collect_results() -> tuple[List[CoverageResult], List[str]]:
    """Run all available measurements.

    Returns:
        A tuple ``(results, gaps)`` where ``results`` is the list of measured
        :class:`CoverageResult` objects and ``gaps`` is a list of human-readable
        notes about apps that could not be measured on this machine.
    """
    results: List[CoverageResult] = []
    gaps: List[str] = []

    # 1. Reproducible Chromium fixture (Electron-class web content).
    fixture = ChromiumFixtureApp()
    if fixture.available:
        with fixture:
            results.append(fixture.measure())
    else:
        gaps.append(
            "Chromium fixture skipped: no Chrome/Edge browser found on this "
            "machine."
        )

    # 2. Owned, real Electron fixture (the literal Electron case).
    electron = ElectronFixtureApp()
    if electron.available:
        with electron:
            results.append(electron.measure())
    else:
        gaps.append(
            "Electron fixture skipped: Electron not installed. Run `npm "
            "install` in benchmarks/recognition/fixtures/electron/."
        )

    # 3. Owned, real Java Swing fixture (the literal Java/Swing JAB case).
    swing = JavaSwingFixtureApp()
    if swing.available:
        with swing:
            results.append(swing.measure())
    else:
        gaps.append(
            "Java Swing fixture skipped: no JDK found. Install a JDK (set "
            "JAVA_HOME) and enable Java Access Bridge (`jabswitch -enable`)."
        )

    # 4. Optional real desktop apps (included only when actually open).
    for spec in OPTIONAL_APPS:
        result = measure_running_app(
            app=spec["app"],
            framework=spec["framework"],
            title_substring=spec["title_substring"],
        )
        if result is not None:
            results.append(result)
        else:
            gaps.append(
                f"{spec['app']} ({spec['framework']}): not running on this "
                f"desktop — no window titled '*{spec['title_substring']}*'."
            )

    # 5. SAP GUI is not available in this environment.
    gaps.append(
        "SAP GUI (SAP scripting/COM): not installed in this environment — "
        "future work."
    )

    return results, gaps


def format_markdown(results: List[CoverageResult], gaps: List[str]) -> str:
    """Render the results as a Markdown table plus a gaps list.

    Args:
        results: Measured coverage results.
        gaps: Human-readable notes about unmeasured apps.

    Returns:
        A Markdown string.
    """
    lines = [
        "| App | Framework | UIA-only | Cascade | Delta | Extra via |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for result in results:
        extra = ", ".join(
            f"{name} (+{count})" for name, count in sorted(result.extra_sources.items())
        ) or "—"
        lines.append(
            f"| {result.app} | {result.framework} | "
            f"{result.uia_only_count} | {result.cascade_count} | "
            f"**+{result.delta}** | {extra} |"
        )
    out = "\n".join(lines)
    if gaps:
        out += "\n\n**Documented gaps (no fabrication):**\n"
        out += "\n".join(f"- {gap}" for gap in gaps)
    return out


def format_human(results: List[CoverageResult], gaps: List[str]) -> str:
    """Render the results as a plain-text table for terminals.

    Args:
        results: Measured coverage results.
        gaps: Human-readable notes about unmeasured apps.

    Returns:
        A plain-text string.
    """
    lines = ["Recognition-coverage benchmark (issue #931)", "=" * 60]
    for result in results:
        lines.append(f"\n{result.app}  [{result.framework}]")
        lines.append(f"  UIA-only baseline : {result.uia_only_count}")
        lines.append(f"  Full cascade      : {result.cascade_count}")
        lines.append(f"  Delta             : +{result.delta}")
        if result.extra_sources:
            extra = ", ".join(
                f"{name} (+{count})"
                for name, count in sorted(result.extra_sources.items())
            )
            lines.append(f"  Extra via         : {extra}")
        if result.sample_extra_names:
            sample = ", ".join(result.sample_extra_names[:6])
            lines.append(f"  Cascade-only ex.  : {sample}")
    if gaps:
        lines.append("\nDocumented gaps (no fabrication):")
        for gap in gaps:
            lines.append(f"  - {gap}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional argument vector (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code (0 on success, 1 if no real delta was measured).
    """
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--json", action="store_true", help="emit JSON")
    group.add_argument("--markdown", action="store_true", help="emit Markdown")
    args = parser.parse_args(argv)

    results, gaps = collect_results()

    if args.json:
        print(json.dumps(
            {
                "results": [r.to_dict() for r in results],
                "gaps": gaps,
            },
            indent=2,
        ))
    elif args.markdown:
        print(format_markdown(results, gaps))
    else:
        print(format_human(results, gaps))

    # Success requires at least one measured app with a positive delta.
    if any(r.delta > 0 for r in results):
        return 0
    print("\nWARNING: no positive recognition delta measured.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
