"""Soak harness — run many recognition+action cycles and detect instability (M4-4).

``run_soak`` drives ``cycle_fn`` N times, sampling per-cycle wall time plus a
resource sample (process RSS MB + watched-app process count) via an injectable
``sampler``. It reports whether the run was stable: **zero failures, zero process
leak, zero memory leak, no timing degradation**.

All timing/resource inputs are injectable (``sampler``, ``clock``), so the
analysis is deterministic and unit-testable with no real processes — the module
is Linux-collectable. The real ≥100-cycle run against real apps lives in a
desktop-gated test and is driven by isolated QA.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

# Timing is "degraded" if the last quarter of cycles averages more than this
# multiple of the first quarter — a runaway slowdown, not normal jitter.
DEGRADE_TIME_FACTOR = 3.0
# Memory "leaks" if RSS grows by more than this from first to last sample.
LEAK_MEM_GROWTH_MB = 50.0


@dataclass
class ResourceSample:
    rss_mb: float
    proc_count: int


@dataclass
class SoakResult:
    cycles: int
    failures: "list[tuple[int, str]]" = field(default_factory=list)
    durations_ms: "list[float]" = field(default_factory=list)
    samples: "list[ResourceSample]" = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return len(self.failures) > 0

    @property
    def process_leaked(self) -> bool:
        if len(self.samples) < 2:
            return False
        return self.samples[-1].proc_count > self.samples[0].proc_count

    @property
    def memory_leaked(self) -> bool:
        if len(self.samples) < 2:
            return False
        return (self.samples[-1].rss_mb - self.samples[0].rss_mb) > LEAK_MEM_GROWTH_MB

    @property
    def time_degraded(self) -> bool:
        n = len(self.durations_ms)
        if n < 8:
            return False
        q = max(1, n // 4)
        first = sum(self.durations_ms[:q]) / q
        last = sum(self.durations_ms[-q:]) / q
        if first <= 0:
            return False
        return last > first * DEGRADE_TIME_FACTOR

    @property
    def ok(self) -> bool:
        return not (self.failed or self.process_leaked or self.memory_leaked or self.time_degraded)

    def summary(self) -> str:
        return (
            f"soak: {self.cycles} cycles, {len(self.failures)} failures, "
            f"proc {self.samples[0].proc_count if self.samples else '?'}"
            f"->{self.samples[-1].proc_count if self.samples else '?'}, "
            f"rss {self.samples[0].rss_mb if self.samples else '?'}"
            f"->{self.samples[-1].rss_mb if self.samples else '?'}MB, "
            f"degraded={self.time_degraded}, ok={self.ok}"
        )


def run_soak(
    cycle_fn: "Callable[[int], None]",
    cycles: int,
    *,
    sampler: "Callable[[], ResourceSample]",
    clock: "Callable[[], float]" = time.perf_counter,
    on_progress: "Callable[[int, SoakResult], None] | None" = None,
) -> SoakResult:
    """Run *cycles* recognition+action cycles and return a :class:`SoakResult`.

    A cycle that raises is recorded as a failure (index + message) and the soak
    continues — one flaky cycle must not abort the run, and the final verdict
    still fails. ``sampler`` is called once per cycle for the resource sample.
    """
    result = SoakResult(cycles=cycles)
    for i in range(cycles):
        t0 = clock()
        try:
            cycle_fn(i)
        except Exception as exc:  # noqa: BLE001 — record any cycle failure, keep going
            result.failures.append((i, f"{type(exc).__name__}: {exc}"))
        result.durations_ms.append((clock() - t0) * 1000.0)
        try:
            result.samples.append(sampler())
        except Exception:  # noqa: BLE001 — a sampler hiccup must not abort the soak
            pass
        if on_progress is not None:
            on_progress(i, result)
    return result


def _current_rss_mb() -> float:
    """Working-set (RSS) of the current process in MB, via psapi. 0.0 on failure."""
    try:
        import ctypes
        from ctypes import wintypes

        class _PMC(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = _PMC()
        counters.cb = ctypes.sizeof(_PMC)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return counters.WorkingSetSize / (1024.0 * 1024.0)
    except Exception:
        pass
    return 0.0


def _watched_proc_count() -> int:
    """Total count of watched GUI-app processes currently running (leak signal)."""
    from tests._process_snapshot import snapshot, tasklist_lister

    snap = snapshot(tasklist_lister)
    return sum(len(pids) for pids in snap.values())


def real_sampler() -> ResourceSample:
    """Live sampler for the real desktop soak: naturo RSS + watched-app count."""
    return ResourceSample(rss_mb=_current_rss_mb(), proc_count=_watched_proc_count())
