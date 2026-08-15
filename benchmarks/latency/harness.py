"""Latency benchmark harness (issue #418).

This harness measures how long naturo's engine takes to perform its core
operations — ``see`` (walk/recognize a window's element tree), ``find`` (locate
a single element by intent) and, by extension, ``click`` — so that performance
regressions between releases can be caught in CI rather than in the field.

Two layers, deliberately separated
----------------------------------
1. **A pure statistics core** — :func:`summarize`, :func:`regression_check` and
   :func:`measure_operation`. These touch neither the desktop nor naturo: they
   take a list of millisecond timings (or a zero-arg callable) and compute
   percentiles / decide pass-fail. This is the hermetically testable part and
   the only code the unit tests exercise.
2. **Thin live-fixture wrappers** — :func:`measure_see_latency` and
   :func:`measure_find_latency`. These drive :func:`naturo.cascade.run_cascade`
   against the *same* offline Chromium fixture the recognition benchmark ships
   (``benchmarks/recognition/fixtures/webapp.html`` under a throwaway Chrome
   user-data-dir with ``--remote-debugging-port``), so the numbers are
   reproducible and offline — no network, no live-website drift. They are the
   CI-run path and require a real interactive desktop; importing this module
   never does (the recognition-harness / naturo imports they need are performed
   lazily inside the functions).

Percentile method
-----------------
Percentiles use the **nearest-rank** method (no interpolation): for ``n`` sorted
samples the ``P``-th percentile is the sample at 1-based ordinal rank
``ceil(P/100 * n)``, clamped to ``[1, n]``. It is exact, order-statistic based,
and returns a value that actually occurred — which keeps regression thresholds
easy to reason about. For ``1..100`` this yields ``p50=50``, ``p90=90``,
``p99=99``.

Public entry points
--------------------
* :func:`summarize` — pure: samples -> :class:`LatencyResult`.
* :func:`regression_check` — pure: is a result within tolerance of a baseline?
* :func:`measure_operation` — time any zero-arg callable ``iterations`` times.
* :func:`measure_see_latency` / :func:`measure_find_latency` — live fixture runs.
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LatencySample:
    """A single timed run of an operation.

    Attributes:
        index: Zero-based iteration index (post-warmup) of this timing.
        elapsed_ms: Wall-clock duration of the run, in milliseconds.
    """

    index: int
    elapsed_ms: float


@dataclass(frozen=True)
class LatencyResult:
    """Aggregated latency statistics for one operation.

    All timing fields are in milliseconds. ``samples`` retains every raw
    per-iteration timing so a caller can recompute or plot the distribution.

    Attributes:
        operation: Operation label (e.g. ``"see"``, ``"find"``, ``"click"``).
        iterations: Number of measured (post-warmup) iterations.
        p50: Median latency (nearest-rank).
        p90: 90th-percentile latency (nearest-rank) — the regression signal.
        p99: 99th-percentile latency (nearest-rank).
        min: Fastest measured run.
        max: Slowest measured run.
        mean: Arithmetic mean of the measured runs.
        samples: Raw per-iteration millisecond timings, in measured order.
    """

    operation: str
    iterations: int
    p50: float
    p90: float
    p99: float
    min: float
    max: float
    mean: float
    samples: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Return a JSON-serialisable representation of the result."""
        return {
            "operation": self.operation,
            "iterations": self.iterations,
            "p50": self.p50,
            "p90": self.p90,
            "p99": self.p99,
            "min": self.min,
            "max": self.max,
            "mean": self.mean,
            "samples": list(self.samples),
        }


def _percentile_nearest_rank(sorted_samples: List[float], pct: float) -> float:
    """Return the ``pct``-th percentile of ``sorted_samples`` (nearest-rank).

    Args:
        sorted_samples: Samples sorted ascending; must be non-empty.
        pct: Percentile in ``[0, 100]``.

    Returns:
        The sample at 1-based ordinal rank ``ceil(pct/100 * n)``, clamped to
        ``[1, n]``.
    """
    n = len(sorted_samples)
    rank = math.ceil((pct / 100.0) * n)
    if rank < 1:
        rank = 1
    elif rank > n:
        rank = n
    return sorted_samples[rank - 1]


def summarize(
    samples_ms: List[float], operation: str, iterations: int
) -> LatencyResult:
    """Compute percentile statistics for a list of millisecond timings.

    Pure and dependency-free — this is the hermetically testable core. It never
    touches the desktop or naturo.

    Args:
        samples_ms: Per-iteration latencies in milliseconds (any order).
        operation: Operation label recorded on the result.
        iterations: Iteration count recorded on the result (usually
            ``len(samples_ms)``, kept explicit so callers can record intent).

    Returns:
        A :class:`LatencyResult` with ``p50``/``p90``/``p99``/``min``/``max``/
        ``mean`` (nearest-rank percentiles) and the raw samples preserved in the
        given order.

    Raises:
        ValueError: If ``samples_ms`` is empty.
    """
    if not samples_ms:
        raise ValueError("summarize() requires at least one sample.")
    ordered = sorted(samples_ms)
    return LatencyResult(
        operation=operation,
        iterations=iterations,
        p50=_percentile_nearest_rank(ordered, 50),
        p90=_percentile_nearest_rank(ordered, 90),
        p99=_percentile_nearest_rank(ordered, 99),
        min=ordered[0],
        max=ordered[-1],
        mean=sum(ordered) / len(ordered),
        samples=list(samples_ms),
    )


def regression_check(
    current: LatencyResult, baseline_ms: float, tolerance_pct: float
) -> tuple[bool, str]:
    """Decide whether ``current`` is a p90 regression against a baseline.

    Pure and testable. The p90 is the regression signal: a single slow outlier
    should not fail the build, but a shift of the bulk of runs should.

    Args:
        current: The freshly measured :class:`LatencyResult`.
        baseline_ms: The known-good p90 latency (milliseconds) to compare to.
        tolerance_pct: Allowed slowdown as a percentage of ``baseline_ms``
            (e.g. ``20.0`` permits the p90 to grow by up to 20%).

    Returns:
        ``(ok, message)`` where ``ok`` is ``False`` when
        ``current.p90 > baseline_ms * (1 + tolerance_pct/100)``. The message is
        human-readable and states the numbers either way. A run exactly at the
        threshold passes (``ok=True``).
    """
    threshold = baseline_ms * (1.0 + tolerance_pct / 100.0)
    ok = current.p90 <= threshold
    if ok:
        message = (
            f"{current.operation}: p90 {current.p90:.2f} ms within budget "
            f"{threshold:.2f} ms (baseline {baseline_ms:.2f} ms "
            f"+{tolerance_pct:.0f}%)."
        )
    else:
        over_pct = (
            (current.p90 - baseline_ms) / baseline_ms * 100.0
            if baseline_ms
            else float("inf")
        )
        message = (
            f"{current.operation}: REGRESSION — p90 {current.p90:.2f} ms "
            f"exceeds budget {threshold:.2f} ms (baseline {baseline_ms:.2f} ms "
            f"+{tolerance_pct:.0f}%); {over_pct:.1f}% over baseline."
        )
    return ok, message


def measure_operation(
    op_name: str,
    fn: Callable[[], object],
    iterations: int = 20,
    warmup: int = 3,
) -> LatencyResult:
    """Time a zero-arg callable ``iterations`` times and summarise the latencies.

    The timer is decoupled from naturo on purpose: ``fn`` is any zero-arg
    callable, so this function is unit-testable with a synthetic closure and is
    the single place the live wrappers funnel through.

    Args:
        op_name: Operation label recorded on the result.
        fn: Zero-argument callable to time. Its return value is ignored.
        iterations: Number of *measured* runs (must be >= 1).
        warmup: Number of initial runs to execute and discard before measuring
            (JIT/first-touch/cache warm-up). Must be >= 0.

    Returns:
        A :class:`LatencyResult` over the ``iterations`` measured runs.

    Raises:
        ValueError: If ``iterations < 1`` or ``warmup < 0``.
    """
    if iterations < 1:
        raise ValueError("iterations must be >= 1.")
    if warmup < 0:
        raise ValueError("warmup must be >= 0.")

    for _ in range(warmup):
        fn()

    samples_ms: List[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        samples_ms.append((time.perf_counter() - start) * 1000.0)

    return summarize(samples_ms, operation=op_name, iterations=iterations)


# ---------------------------------------------------------------------------
# Live-desktop fixture wrappers (the CI-run path).
#
# Everything below drives a real desktop. The naturo / recognition-harness
# imports are performed lazily *inside* the functions so that importing this
# module never requires a live desktop or the cdp extra.
# ---------------------------------------------------------------------------


def _cascade_callable(backend, hwnd: int, pid: Optional[int], depth: int):
    """Build a zero-arg callable that runs one full cascade over a window.

    Args:
        backend: A naturo backend (from ``get_backend()``).
        hwnd: Target window handle.
        pid: Target process id (aids CDP/JAB discovery).
        depth: Maximum accessibility-tree depth to walk.

    Returns:
        A zero-argument callable suitable for :func:`measure_operation`.
    """
    from naturo.cascade import run_cascade

    def _run() -> object:
        return run_cascade(
            backend, hwnd=hwnd, pid=pid, depth=depth, backend_name="auto"
        )

    return _run


def measure_see_latency(
    *,
    iterations: int = 20,
    warmup: int = 3,
    depth: int = 15,
) -> LatencyResult:
    """Measure ``see`` latency: full-cascade recognition of the Chromium fixture.

    Launches the bundled offline Chromium fixture (reusing the recognition
    harness's :class:`~benchmarks.recognition.harness.ChromiumFixtureApp`), then
    times a full ``run_cascade`` walk of its window ``iterations`` times. This is
    the live CI path — do not call it without a real desktop.

    Args:
        iterations: Number of measured cascade runs.
        warmup: Number of discarded warm-up runs.
        depth: Maximum accessibility-tree depth to walk.

    Returns:
        A :class:`LatencyResult` labelled ``"see"``.

    Raises:
        RuntimeError: If the fixture browser is unavailable or its window cannot
            be located.
    """
    from benchmarks.recognition.harness import ChromiumFixtureApp
    from naturo.backends.base import get_backend

    fixture = ChromiumFixtureApp()
    if not fixture.available:
        raise RuntimeError(
            "Chromium fixture unavailable: no Chrome/Edge browser found."
        )
    with fixture:
        window = fixture.find_window()
        if window is None:
            raise RuntimeError("Could not locate the Chromium fixture window.")
        backend = get_backend()
        fn = _cascade_callable(backend, window.hwnd, window.pid, depth)
        logger.info("Measuring see latency over %d iterations", iterations)
        return measure_operation("see", fn, iterations=iterations, warmup=warmup)


def measure_find_latency(
    *,
    match: str = "button",
    iterations: int = 20,
    warmup: int = 3,
    depth: int = 15,
) -> LatencyResult:
    """Measure ``find`` latency: locate a single element by intent in the fixture.

    Reuses the same offline Chromium fixture as :func:`measure_see_latency`, but
    each timed run walks the cascade and then filters the flattened tree for the
    first element whose name/role matches ``match`` — the ``find`` code path.
    Live CI path; requires a real desktop.

    Args:
        match: Case-insensitive substring to match against element name/role.
        iterations: Number of measured find runs.
        warmup: Number of discarded warm-up runs.
        depth: Maximum accessibility-tree depth to walk.

    Returns:
        A :class:`LatencyResult` labelled ``"find"``.

    Raises:
        RuntimeError: If the fixture browser is unavailable or its window cannot
            be located.
    """
    from benchmarks.recognition.harness import ChromiumFixtureApp
    from naturo.backends.base import get_backend
    from naturo.cascade import _flatten, run_cascade

    fixture = ChromiumFixtureApp()
    if not fixture.available:
        raise RuntimeError(
            "Chromium fixture unavailable: no Chrome/Edge browser found."
        )
    needle = match.lower()
    with fixture:
        window = fixture.find_window()
        if window is None:
            raise RuntimeError("Could not locate the Chromium fixture window.")
        backend = get_backend()

        def _find() -> object:
            result = run_cascade(
                backend,
                hwnd=window.hwnd,
                pid=window.pid,
                depth=depth,
                backend_name="auto",
            )
            if result.tree is None:
                return None
            for element in _flatten(result.tree):
                label = f"{element.name or ''} {element.role or ''}".lower()
                if needle in label:
                    return element
            return None

        logger.info("Measuring find latency over %d iterations", iterations)
        return measure_operation("find", _find, iterations=iterations, warmup=warmup)
