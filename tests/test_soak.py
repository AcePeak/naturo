"""M4 criterion 4 — unit tests for the soak harness verdict logic.

Deterministic injected clock + sampler + cycle_fn — no real processes, apps, or
timing, so the module is Linux-collectable. Proves the harness flags failures,
process leaks, memory leaks, and timing degradation, and stays green on a stable
run.
"""
from __future__ import annotations

from tests._soak import LEAK_MEM_GROWTH_MB, ResourceSample, run_soak


class _Clock:
    """Fake monotonic clock yielding t0,t1 pairs so each cycle has *durations[i]* seconds."""

    def __init__(self, durations_s):
        self._vals = []
        t = 0.0
        for d in durations_s:
            self._vals.append(t)          # t0
            self._vals.append(t + d)      # t1
            t += d + 1.0
        self._i = 0

    def __call__(self):
        v = self._vals[self._i]
        self._i += 1
        return v


def _sampler(samples):
    it = iter(samples)
    return lambda: next(it)


def _stable_samples(n, rss=100.0, proc=2):
    return [ResourceSample(rss_mb=rss, proc_count=proc) for _ in range(n)]


def test_stable_run_is_ok():
    n = 12
    res = run_soak(
        lambda i: None, n,
        sampler=_sampler(_stable_samples(n)),
        clock=_Clock([0.001] * n),
    )
    assert not res.failed and not res.process_leaked
    assert not res.memory_leaked and not res.time_degraded
    assert res.ok is True
    assert len(res.durations_ms) == n and len(res.samples) == n


def test_failure_is_recorded_and_soak_continues():
    n = 10

    def cycle(i):
        if i == 3:
            raise RuntimeError("boom")

    res = run_soak(cycle, n, sampler=_sampler(_stable_samples(n)), clock=_Clock([0.001] * n))
    assert res.failed and len(res.failures) == 1
    assert res.failures[0][0] == 3 and "boom" in res.failures[0][1]
    assert len(res.durations_ms) == n  # continued through all cycles
    assert res.ok is False


def test_process_leak_detected():
    n = 10
    samples = [ResourceSample(100.0, 2) for _ in range(n - 1)] + [ResourceSample(100.0, 5)]
    res = run_soak(lambda i: None, n, sampler=_sampler(samples), clock=_Clock([0.001] * n))
    assert res.process_leaked is True
    assert res.ok is False


def test_memory_leak_detected():
    n = 10
    samples = [ResourceSample(100.0, 2) for _ in range(n - 1)] + [
        ResourceSample(100.0 + LEAK_MEM_GROWTH_MB + 10, 2)
    ]
    res = run_soak(lambda i: None, n, sampler=_sampler(samples), clock=_Clock([0.001] * n))
    assert res.memory_leaked is True
    assert res.ok is False


def test_time_degradation_detected():
    n = 20
    durations = [0.001] * 15 + [0.01] * 5  # last quarter ~10x the first quarter
    res = run_soak(lambda i: None, n, sampler=_sampler(_stable_samples(n)), clock=_Clock(durations))
    assert res.time_degraded is True
    assert res.ok is False


def test_no_degradation_flag_with_too_few_cycles():
    n = 4
    res = run_soak(lambda i: None, n, sampler=_sampler(_stable_samples(n)),
                   clock=_Clock([0.001, 0.001, 0.001, 1.0]))
    assert res.time_degraded is False  # not enough data to judge a trend


def test_summary_is_descriptive():
    n = 10
    res = run_soak(lambda i: None, n, sampler=_sampler(_stable_samples(n)), clock=_Clock([0.001] * n))
    s = res.summary()
    assert "cycles" in s and "ok=True" in s
