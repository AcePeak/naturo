# Latency benchmark (`benchmarks/latency/`)

Tracks naturo engine operation latency over time so **performance regressions
between releases** are caught in CI rather than in the field (issue #418).

Sibling to `benchmarks/recognition/` and `benchmarks/competitive/`; it reuses the
same offline Chromium fixture those harnesses ship.

## What it measures

| Operation | What is timed |
| --- | --- |
| `see`  | One full `run_cascade` walk (recognize the whole element tree of a window). |
| `find` | One full `run_cascade` walk **plus** filtering the flattened tree for the first element matching an intent — the `find` code path. `click` targeting resolves through the same locate cost, so `find` is its proxy. |

For each operation the harness reports `p50`, `p90`, `p99`, `min`, `max`, `mean`
(all milliseconds) plus the raw per-iteration samples. Warm-up runs are discarded
before measurement.

The **p90** is the regression signal: a single slow outlier will not fail the
build, but a shift of the bulk of runs will.

## Why the fixture makes it reproducible / offline

The live measurements drive a Chromium browser on the bundled local page
`benchmarks/recognition/fixtures/webapp.html`, launched under a throwaway Chrome
user-data-dir with `--remote-debugging-port` (via the recognition harness's
`ChromiumFixtureApp`). No network, no live-website drift, no login — so run-to-run
latency reflects naturo's engine, not the internet. Electron apps embed the same
Chromium content layer, so the numbers are representative of real CDP-backed
targets.

## Layers

- **Pure core** (`harness.py`): `summarize`, `regression_check`,
  `measure_operation`. No desktop, no naturo — this is what
  `tests/test_latency_benchmark.py` covers hermetically.
- **Live wrappers** (`harness.py`): `measure_see_latency`, `measure_find_latency`.
  Thin adapters over `measure_operation` + `run_cascade`. Their naturo imports are
  lazy, so importing the module never needs a desktop.

Percentiles use the **nearest-rank** method (no interpolation): for `n` sorted
samples the `P`-th percentile is the sample at 1-based rank `ceil(P/100 * n)`.
It is exact and returns a value that actually occurred. For `1..100` this gives
`p50=50`, `p90=90`, `p99=99`.

## Running

```sh
# Live run against the offline fixture (needs a real desktop + Chrome/Edge + cdp extra):
python -m benchmarks.latency.run_latency

# Assemble + validate only, nothing live (safe on headless CI lint/import stages):
python -m benchmarks.latency.run_latency --check

# Compare a live run against the committed baseline; exits non-zero on p90 regression:
python -m benchmarks.latency.run_latency --baseline benchmarks/latency/baseline.json
```

## Regenerating the baseline

`baseline.json` ships **placeholder-but-plausible** p90 budgets. To refresh them,
run the benchmark on a **known-good runner** (the same class of machine CI uses),
read the measured `p90` for each operation from the JSON report, and copy those
values into `operations.<op>.p90_ms`. Do **not** hand-tune the numbers — a baseline
is only meaningful if it came from a real run. `tolerance_pct` is a policy knob
(allowed p90 slowdown before failure), not a measurement, so it is set by hand.

## How CI consumes it

The GitHub Actions perf stage runs `run_latency.py --baseline benchmarks/latency/baseline.json`
on a Windows runner with Chrome installed, prints the JSON report as a build
artifact for trend tracking, and fails the job when `regression_check` reports any
operation's p90 over budget.

> **Note:** the actual GitHub Actions workflow file is delivered **separately**
> (adding/editing anything under `.github/` needs `workflow`-scope push) and is
> **not** part of this branch.
