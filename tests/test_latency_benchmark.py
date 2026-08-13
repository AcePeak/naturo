"""Hermetic tests for the latency benchmark harness (issue #418).

These tests exercise only the pure statistics core — ``summarize``,
``regression_check`` and ``measure_operation`` with a synthetic callable — plus
JSON round-tripping. No live desktop, no naturo input, no temp-dir tricks.
"""
from __future__ import annotations

import json

import pytest

from benchmarks.latency.harness import (
    LatencyResult,
    measure_operation,
    regression_check,
    summarize,
)


# --------------------------------------------------------------------------- #
# summarize — percentile correctness
# --------------------------------------------------------------------------- #
def test_summarize_percentiles_on_1_to_100() -> None:
    """Nearest-rank percentiles of 1..100 land on the expected order statistics."""
    samples = [float(i) for i in range(1, 101)]
    result = summarize(samples, operation="see", iterations=100)
    assert result.p50 == 50.0
    assert result.p90 == 90.0
    assert result.p99 == 99.0
    assert result.min == 1.0
    assert result.max == 100.0
    assert result.mean == pytest.approx(50.5)
    assert result.iterations == 100


def test_summarize_is_order_independent() -> None:
    """Unsorted input yields the same percentiles as sorted input."""
    import random

    ascending = [float(i) for i in range(1, 101)]
    jumbled = list(ascending)
    random.Random(42).shuffle(jumbled)
    a = summarize(ascending, "see", 100)
    b = summarize(list(reversed(ascending)), "see", 100)
    c = summarize(jumbled, "see", 100)
    assert (a.p50, a.p90, a.p99) == (b.p50, b.p90, b.p99) == (c.p50, c.p90, c.p99)


def test_summarize_single_sample() -> None:
    """A single sample is every percentile, the min, the max and the mean."""
    result = summarize([12.5], operation="find", iterations=1)
    assert result.p50 == result.p90 == result.p99 == 12.5
    assert result.min == result.max == result.mean == 12.5
    assert result.samples == [12.5]


def test_summarize_all_equal() -> None:
    """When every sample is equal, all stats collapse to that value."""
    result = summarize([7.0] * 10, operation="click", iterations=10)
    assert result.p50 == result.p90 == result.p99 == 7.0
    assert result.min == result.max == result.mean == 7.0


def test_summarize_preserves_raw_order() -> None:
    """The raw ``samples`` list keeps the caller's original ordering."""
    given = [3.0, 1.0, 2.0]
    result = summarize(given, operation="see", iterations=3)
    assert result.samples == [3.0, 1.0, 2.0]


def test_summarize_rejects_empty() -> None:
    """An empty sample list is a programming error."""
    with pytest.raises(ValueError):
        summarize([], operation="see", iterations=0)


# --------------------------------------------------------------------------- #
# regression_check — tolerance / boundary
# --------------------------------------------------------------------------- #
def _result_with_p90(p90: float) -> LatencyResult:
    return summarize([p90], operation="see", iterations=1)


def test_regression_check_within_tolerance_passes() -> None:
    """A p90 comfortably under budget passes."""
    ok, message = regression_check(_result_with_p90(100.0), baseline_ms=100.0, tolerance_pct=20.0)
    assert ok is True
    assert "within budget" in message


def test_regression_check_beyond_tolerance_fails() -> None:
    """A p90 above the budget fails and the message flags a regression."""
    ok, message = regression_check(_result_with_p90(130.0), baseline_ms=100.0, tolerance_pct=20.0)
    assert ok is False
    assert "REGRESSION" in message


def test_regression_check_exactly_at_threshold_passes() -> None:
    """A p90 exactly on the threshold (baseline * (1 + tol)) is allowed."""
    # baseline 100 + 20% => threshold 120.0
    ok, _ = regression_check(_result_with_p90(120.0), baseline_ms=100.0, tolerance_pct=20.0)
    assert ok is True


def test_regression_check_just_over_threshold_fails() -> None:
    """One unit over the threshold fails."""
    ok, _ = regression_check(_result_with_p90(120.001), baseline_ms=100.0, tolerance_pct=20.0)
    assert ok is False


# --------------------------------------------------------------------------- #
# measure_operation — synthetic callable
# --------------------------------------------------------------------------- #
def test_measure_operation_counts_iterations_and_warmup() -> None:
    """``fn`` is called ``warmup + iterations`` times; result counts measured only."""
    calls = {"n": 0}

    def fn() -> None:
        calls["n"] += 1

    result = measure_operation("synthetic", fn, iterations=5, warmup=2)
    assert calls["n"] == 7  # 2 warmup + 5 measured
    assert result.iterations == 5
    assert len(result.samples) == 5
    assert result.operation == "synthetic"


def test_measure_operation_stats_are_monotonic() -> None:
    """min <= mean <= max holds for real measured timings."""
    result = measure_operation("noop", lambda: None, iterations=10, warmup=1)
    assert result.min <= result.mean <= result.max
    assert result.p50 <= result.p99
    assert all(s >= 0.0 for s in result.samples)


def test_measure_operation_rejects_bad_args() -> None:
    """Zero iterations and negative warmup are rejected."""
    with pytest.raises(ValueError):
        measure_operation("x", lambda: None, iterations=0)
    with pytest.raises(ValueError):
        measure_operation("x", lambda: None, iterations=1, warmup=-1)


# --------------------------------------------------------------------------- #
# JSON round-trip
# --------------------------------------------------------------------------- #
def test_latency_result_json_round_trip() -> None:
    """``to_dict`` -> ``json.dumps`` -> ``json.loads`` preserves every field."""
    result = summarize([1.0, 2.0, 3.0, 4.0], operation="find", iterations=4)
    payload = result.to_dict()
    restored = json.loads(json.dumps(payload))
    assert restored["operation"] == "find"
    assert restored["iterations"] == 4
    assert restored["p50"] == result.p50
    assert restored["p90"] == result.p90
    assert restored["p99"] == result.p99
    assert restored["min"] == 1.0
    assert restored["max"] == 4.0
    assert restored["mean"] == pytest.approx(2.5)
    assert restored["samples"] == [1.0, 2.0, 3.0, 4.0]
