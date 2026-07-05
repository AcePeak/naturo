# naturo — round progress log

Plain-language, one entry per `/goal` round: capability delivered → distance to
the current milestone → next. Newest first.

---

## 2026-07-03 — D1 slice 1: competitive harness scaffold (real rivals)

**Milestone:** D1 — prove #1 via a public, reproducible competitive coverage
matrix vs OSS rivals. **Was unstarted** (only `benchmarks/recognition/` existed;
`docs/COMPETITIVE.md`'s matrix was claim-based, dated 2026-06-16 — not from
runs). Issue #1233.

**Capability delivered this round:** the `benchmarks/competitive/` harness — the
missing piece that lets the coverage matrix be *reproduced from real runs* rather
than authored. Unlike `benchmarks/recognition/` (naturo cascade vs naturo's own
UIA-only baseline — a fair proxy), this runs the **actual installed rival
libraries** on the **same** window:

- `matrix.py` — pure aggregation + Markdown rendering (imports neither naturo nor
  rivals → Linux-collectable; the test-pinned core). Cells: `✓ (n)` recognized /
  `✗ (0)` ran-but-saw-nothing (the moat cell) / `blocked: needs env`. naturo's own
  gaps render the same way — no cherry-picking.
- `harness.py` — one `Adapter` per tool: **naturo** (fused cascade), **pywinauto**
  (walks its UIA control tree — strongest UIA-only rival), **PyAutoGUI** (no
  element model → honest constant 0). A tool that can't run → `None` →
  `blocked: needs env`, never a guessed number.
- `run_competitive.py` — Windows runner; reuses the recognition fixtures
  (Chromium / real Electron / Java-Swing / Excel-COM) + a UIA-native app.
- `tests/test_competitive_benchmark.py` — 9 tests pinning the matrix logic
  (cell classes, moat detection, honest rendering). Linux-collectable, green.
- `competitive` extra in pyproject (pywinauto + pyautogui, win32-guarded).

**Verification:** ruff clean; 9/9 pytest green on macOS; guarded imports confirmed
(rivals → `blocked` off-Windows, PyAutoGUI honest 0); independent fresh-context
agent re-ran + adversarially probed the matrix logic. **No numbers were written
into `docs/COMPETITIVE.md`** — fabrication would violate D1's honesty rule.

**Distance to D1:** criteria **#1 (runnable harness)** and **#4 (matrix-logic
test, pytest exits 0, Linux-collectable)** met. Remaining: **#2/#3** — run the
harness on a real Windows desktop with the rivals installed and *regenerate the
`docs/COMPETITIVE.md` matrix from that output* (independent QA re-runs to confirm
the numbers aren't hand-authored); **#5** — the README "beats X" positioning stays
Ace-gated.

**Next round:** Windows-runner slice — `pip install .[competitive,cdp]`, run
`python -m benchmarks.competitive.run_competitive --markdown` on the fixtures,
paste the real matrix into `docs/COMPETITIVE.md`, and have QA independently
reproduce it.

---

## Orc note — 2026-07-05 (next-round slice is now decision-ready)

The next non-Ace-gated D1 slice — the **meaningful-interactive-element metric** — is now fully
spec'd in `docs/design/MEANINGFUL_INTERACTIVE_ELEMENT_METRIC.md`. It resolves the `docs/COMPETITIVE.md`
self-contradiction (raw `len(window.descendants())` inflates Chrome/Excel for a UIA-only rival) by
applying a **symmetric** interactive role/pattern filter across all adapters, retaining the raw count,
and leaving the Java/SAP/deep-CEF `✗` moat cells untouched. Design is settled → a `/goal` round can go
straight to TDD build → independent-verify → land, no re-deliberation. This may recover the
Electron/Excel cells on the merits and shrink the D1 #5 Ace gate. **This is the recommended next round.**
