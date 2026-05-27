# QA Status
Last updated: 2026-05-28 03:21
Current round: 123
Current milestone: v0.3.2 (23 open / 88 closed, 79%)

## This Round
- Persona: Chinese User (hour 03 % 8 = 3)
- CI Desktop Tests: 0 passed, 0 failed, **151 skipped** (no interactive desktop, #863). `.last-ci-sha` advanced `cf3e1fd` → `099c2bb`.
- Targeted unit tests for the 3 untouched `status:done` issues:
  - #807 (PR #845, `test_cli_press.py`): **66/66 PASS**
  - #788 (PR #820, 5 test files): **88 passed, 3 FAILED on Windows** (broken tests — filed #870)
  - #786 (PR #815, 3 test files): **16/16 PASS**
- Issues verified + closed: **none** — partial-verification comments posted on #807, #786, #788 (with #870 cross-reference). All 5 status:done still blocked on #863.
- E2E tests: skipped (no desktop). MCP `tools list` smoke-tested: 64 tools enumerated, exit 0.
- Regression (Phase 5): TC-0041 consec 33, TC-0046 consec 24, TC-0053 partial (success branch blocked by #863), TC-0052/#864/TC-0054/#866/TC-0055/#867/TC-0057/#869 fail (unchanged — no fixes landed).
- New issues created:
  - **#870** (bug, P2, from:qa, v0.3.2) — 3 unit tests added by PR #820 fail on Windows; missing `skipif`/platform guard
  - **#871** (bug, P2, from:qa, v0.3.4) — Window-targeting flag matrix (--window/--hwnd/--pid) inconsistent across subcommands. Discovered during Chinese User simulation (`naturo list windows --window 记事本`).
- Existing issues updated: comments on #807/#786/#788 (partial-verify), #788 cross-referenced to #870.
- New test cases created: **TC-0058** (`exploratory/window-targeting-flag-matrix.yaml`, sources #871).
- Test cases retired: none.
- Total active test cases: 36 active / 23 retired.
- Tests run: 170 unit (66+88+16) + 5 regression/exploratory TCs + ~20 exploratory probes including window-flag matrix sweep.

## Status:done queue
- Started: 5
- Verified + closed: 0
- Rejected: 0
- Partial-verify, retained: 5 (no movement from rounds 117–122)
- **End of round**: 5 (#786, #788, #807, #840, #843) — all still blocked on #863

## Top 3 Risks
1. **#863 (P0 ship gate)** — UIPI/RDP session-binding blocker, day 2 since escalation. Without console-session QA access, v0.3.2 cannot ship. Workaround = launch QA from console session.
2. **#870 (new this round)** — 3 Windows unit tests have been silently failing since PR #820 merged 53 days ago. Self-hosted runner (#842, day 59 offline) and cloud VM (#860, day 21 unassigned) mean Windows-only failures go unnoticed.
3. **CLI contract debt** — 6 v0.3.4 CLI consistency bugs filed in the last 7 days (#864, #865, #866, #867, #869, #871). Needs a coherent flag spec before #92 (semver API stability) can land.

## Persona Coverage (rolling)
| Persona | Last round | Findings |
|---------|-----------|----------|
| First-time User (0) | R120 | #867 (snapshot typo leak) |
| AI Agent Builder (1) | R121 | #868 (MCP capture_screen black PNG) |
| Enterprise RPA Dev (2) | R122 | #869 (deps prompt leaks into -j JSON) |
| Chinese User (3) | **R123** | **#871 (window-targeting flag matrix)** |
| Power User (4) | — | next |
| Accessibility User (5) | — | next |
| Scripter (6) | R118 | #864/#865/#866 (CLI contract trio) |
| Skeptical Evaluator (7) | — | next |
