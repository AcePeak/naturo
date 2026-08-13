"""Run the latency benchmark and emit a JSON report (issue #418).

Usage::

    python -m benchmarks.latency.run_latency                      # run live + JSON
    python -m benchmarks.latency.run_latency --check              # assemble only
    python -m benchmarks.latency.run_latency --baseline baseline.json

``--check`` validates that the harness assembles and the baseline file parses
*without* running anything live — it is what non-desktop CI (lint/import stages)
can call to prove the module is wired up. The default run drives the offline
Chromium fixture and prints ``{operation: {p50, p90, p99, min, max, mean, ...}}``.

``--baseline <path>`` compares each measured operation's p90 against the committed
baseline via :func:`benchmarks.latency.harness.regression_check` and exits
non-zero if any operation regressed beyond its tolerance.

This script's live path requires a real interactive Windows desktop plus a
Chrome/Edge install and the ``cdp`` extra (``pip install naturo[cdp]``). The
GitHub Actions stage that consumes the JSON is delivered separately (it needs
``workflow``-scope push) and is intentionally not part of this branch.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

from benchmarks.latency.harness import (
    LatencyResult,
    measure_find_latency,
    measure_see_latency,
    regression_check,
)

DEFAULT_BASELINE = Path(__file__).resolve().parent / "baseline.json"
#: Default tolerance (percent) applied when the baseline file omits its own.
DEFAULT_TOLERANCE_PCT = 25.0


def collect_results(iterations: int = 20, warmup: int = 3) -> List[LatencyResult]:
    """Run every live latency measurement against the offline fixture.

    Args:
        iterations: Measured iterations per operation.
        warmup: Discarded warm-up iterations per operation.

    Returns:
        The measured :class:`LatencyResult` objects (``see`` then ``find``).
    """
    return [
        measure_see_latency(iterations=iterations, warmup=warmup),
        measure_find_latency(iterations=iterations, warmup=warmup),
    ]


def load_baseline(path: Path) -> dict:
    """Load and minimally validate a baseline JSON file.

    Args:
        path: Path to the baseline JSON.

    Returns:
        The parsed baseline mapping.

    Raises:
        ValueError: If the file is missing an ``operations`` mapping.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("operations"), dict):
        raise ValueError(
            f"Baseline {path} must contain an 'operations' object mapping "
            "operation name -> {{p90_ms, tolerance_pct}}."
        )
    return data


def evaluate_regressions(
    results: List[LatencyResult], baseline: dict
) -> tuple[bool, List[str]]:
    """Compare measured results against a baseline mapping.

    Args:
        results: Measured latency results.
        baseline: A parsed baseline (see :func:`load_baseline`).

    Returns:
        ``(all_ok, messages)`` where ``all_ok`` is ``False`` if any measured
        operation present in the baseline regressed beyond its tolerance.
    """
    operations = baseline.get("operations", {})
    default_tol = float(baseline.get("default_tolerance_pct", DEFAULT_TOLERANCE_PCT))
    all_ok = True
    messages: List[str] = []
    for result in results:
        spec = operations.get(result.operation)
        if spec is None:
            messages.append(
                f"{result.operation}: no baseline entry — skipped (not a gate)."
            )
            continue
        baseline_ms = float(spec["p90_ms"])
        tolerance_pct = float(spec.get("tolerance_pct", default_tol))
        ok, message = regression_check(result, baseline_ms, tolerance_pct)
        all_ok = all_ok and ok
        messages.append(message)
    return all_ok, messages


def build_report(results: List[LatencyResult]) -> Dict[str, dict]:
    """Assemble the ``{operation: stats}`` JSON report body."""
    return {result.operation: result.to_dict() for result in results}


def main(argv: List[str] | None = None) -> int:
    """CLI entry point.

    Args:
        argv: Optional argument vector (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code: 0 on success, 1 on a detected p90 regression or a
        ``--check`` assembly failure.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="assemble and validate without running anything live",
    )
    parser.add_argument(
        "--baseline",
        metavar="PATH",
        help="compare measured p90s against a committed baseline JSON and exit "
        "non-zero on regression",
    )
    parser.add_argument(
        "--iterations", type=int, default=20, help="measured iterations per op"
    )
    parser.add_argument(
        "--warmup", type=int, default=3, help="discarded warm-up iterations per op"
    )
    args = parser.parse_args(argv)

    if args.check:
        # Non-live: prove the harness imports, the callables exist, and the
        # default baseline parses. Runs nothing against the desktop.
        baseline_path = Path(args.baseline) if args.baseline else DEFAULT_BASELINE
        try:
            baseline = load_baseline(baseline_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print(f"--check FAILED: {exc}", file=sys.stderr)
            return 1
        ops = sorted(baseline.get("operations", {}))
        assert callable(measure_see_latency)
        assert callable(measure_find_latency)
        print(
            json.dumps(
                {
                    "check": "ok",
                    "baseline": str(baseline_path),
                    "baseline_operations": ops,
                    "measurable_operations": ["see", "find"],
                },
                indent=2,
            )
        )
        return 0

    results = collect_results(iterations=args.iterations, warmup=args.warmup)
    report = build_report(results)

    if args.baseline:
        baseline = load_baseline(Path(args.baseline))
        all_ok, messages = evaluate_regressions(results, baseline)
        print(json.dumps({"report": report, "regressions": messages}, indent=2))
        if not all_ok:
            print("\nLATENCY REGRESSION DETECTED.", file=sys.stderr)
            return 1
        return 0

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
