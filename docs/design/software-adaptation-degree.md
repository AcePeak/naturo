# ADR: Software Adaptation-Degree Table (M2)

Status: **accepted** · Milestone: **M2** · Feeds: `docs/SOFTWARE_ADAPTATION.md`
(published table) · Builds on: the #931 harness (`benchmarks/recognition/harness.py`)
and the M1 Unified Auto Element Tree (`docs/RECOGNITION_TREE.md`).

This ADR fixes the schema, scoring, and **reproducibility rules** for naturo's
public per-software adaptation-degree table so every later M2 slice composes
coherently and the published numbers are honest and re-runnable.

---

## 1. What "adaptation degree" means

For one target application, the **adaptation degree** answers: *how well, and with
what correctness guarantee, does naturo recognize this software's UI?* It is derived
**only from real measurements** produced by the #931 harness on the host that runs
it — never hand-authored.

Per software we report:

- `frameworks` — the recognition techniques that actually fired (from the fused
  tree's `techniques[]`, M1), e.g. `["uia", "cdp"]`.
- `uia_only_count` / `cascade_count` / `delta` — element counts (existing harness
  `CoverageResult`): what a UIA-only rival sees vs. naturo's full cascade.
- `correctness` — distribution over the fused nodes: `deterministic` vs `uncertain`
  (from M1 `recognition_summary`). Uncertain-only nodes (image/OCR/AI) are counted
  separately and flagged.
- `degree` — a coarse **class**, not a fake precise score (see §2).

## 2. Scoring — a class, not a false-precision number

Correctness-first (GOAL): we do **not** invent a 0–100 score that implies accuracy
we cannot justify. The degree is one of four honest classes:

| degree            | meaning                                                                 |
| ----------------- | ----------------------------------------------------------------------- |
| `full`            | cascade recovers substantially more than UIA-only (`delta > 0`) via a **deterministic** non-UIA framework (cdp/jab/com/ia2/msaa). The moat case. |
| `uia-only`        | only UIA fires; no non-UIA framework adds elements. naturo works but so would a UIA-only rival. |
| `uncertain-only`  | the only non-UIA contribution is image/OCR/AI (uncertain). Recognized, but **warned** — bounds estimated. |
| `blocked: needs env` | the framework naturo *would* use is not exercisable on this host (missing app, missing engine, or a known defect). **Not counted** as coverage. |

`delta`, counts and the fired frameworks are always shown as the underlying
evidence, so the class is auditable.

## 3. Reproducibility rule (non-negotiable)

Every number comes from `benchmarks/recognition/` run **live on the measuring host**.
A framework that cannot be exercised here is recorded as `blocked: needs env` with the
concrete reason and **excluded from any "we support N frameworks" count**. No fabricated
rows. This mirrors the harness's existing "documented gaps (no fabrication)" list.

## 4. Data-model change (Slice B)

Extend `CoverageResult` (harness) with two fields, populated from the fused tree's
`recognition_summary` (M1), keeping full backward compatibility of existing fields:

```python
techniques: list[str] = []          # deterministic-first, e.g. ["uia","cdp"]
correctness_counts: dict = {}        # {"deterministic": N, "uncertain": M}
```

`measure_window` already runs the full cascade; it will additionally call
`recognition_summary(full.tree)` and fill these. `degree` (§2) is a pure function of
`(delta, techniques, correctness_counts)` — unit-testable, Linux-collectable.

## 5. Host reproducibility matrix (THIS machine, measured 2026-07-01)

Recorded from live probes; re-derive per host. Only ✓ rows count toward coverage.

> **Update (2026-07-01, after provisioning):** several rows below were an initial
> snapshot and are now superseded — `jab` is **reproducible** (the source handshake
> #1174 was already correct; only the *local dev DLL* was stale — rebuilt with the
> VS2022 Build Tools that ARE installed; the earlier "MSVC absent / #1213" note was
> wrong, #1213 is an unrelated issue and #1096 is the real, already-fixed handshake
> bug); `ocr` is **reproducible** (`rapidocr_onnxruntime` installed — local, no cloud
> key); `ia2` is a **candidate** (Firefox now installed, additive path not yet wired).
> The authoritative current per-software matrix is `docs/SOFTWARE_ADAPTATION.md`.

| framework | technique | status on this host | evidence |
| --------- | --------- | ------------------- | -------- |
| Win32/UWP/WPF | `uia` | ✓ reproducible | M1 QA: Notepad 46 nodes deterministic |
| Electron/Chromium | `cdp` | ✓ reproducible | M1 QA: Chrome uia+cdp fusion |
| Java Swing/AWT | `jab` | ✗ blocked: needs env | native `naturo_core.dll` handshake defect (#1096); MSVC absent → cannot rebuild here |
| Firefox/IA2 | `ia2` | ✗ blocked: needs env | no Firefox/Thunderbird/LibreOffice installed |
| Office COM | `com` | ⚑ candidate (unwired) | Excel + Word installed; not yet a cascade provider |
| Legacy MSAA | `msaa` | ⚑ candidate (suppressed) | in primary loop but first-non-empty (uia) wins; no additive path yet |
| Image/OCR | `image` | ✗ blocked: needs env | no tesseract/pytesseract/easyocr/cv2/numpy on host (PIL only) |

## 6. M2 slice plan (one per round, each with independent QA)

- **A · ADR** (this doc). ✔
- **B · Harness captures correctness** — add `techniques` + `correctness_counts` to
  `CoverageResult` from `recognition_summary`; TDD, Linux-collectable. Unblocked.
- **C · Broaden a reproducible framework** — the two tractable-here candidates are
  **COM/Excel** (installed) and **MSAA-additive** (native, like the JAB/CDP additive
  path). Deliver ≥2 non-UIA/CDP frameworks that fuse+tag in `see --cascade --json`
  **reproducibly on this host**, deterministic-preferred. If a candidate proves
  non-reproducible on measurement, it is recorded `blocked: needs env`, and the
  criterion's "≥2" is met only by frameworks that genuinely fire here.
- **D · Publish** `docs/SOFTWARE_ADAPTATION.md` from a real `run_benchmark` pass
  (with the §5 blocked rows documented, not counted).
- **E · Independent real-app QA** on the newly-covered frameworks (zero orphaned
  processes, PID-scoped teardown incl. dismissing Save/Don't-Save), then merge to
  `develop` with CI green (auto-merge enabled).

## 7. Honesty note

An earlier session narration (during a host tool-output-corruption stretch) invented a
non-existent benchmark layout (`schema.py`/`apps.py`/`matrix.py`). The real harness is
`harness.py` + `run_benchmark.py` (verified via `git ls-files` and clean line-by-line
reads). This ADR is grounded only in re-verified facts.
