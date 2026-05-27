# QA Status
Last updated: 2026-05-28 05:08
Current round: 125
Current milestone: v0.3.2 (21 open / 88 closed, 81%)

## This Round
- Persona: Accessibility User (hour 05 % 8 = 5)
- CI Desktop Tests: ran (138 desktop+integration skipped, 13 e2e skipped, **0 failed**) on ce8c21a. Only QA report `[skip ci]` commits since last run, but ran anyway per prompt. .last-ci-sha updated.
- Session unchanged from R124: non-interactive (SSH/service class). All `see/capture/list/type/press/click` return `NO_DESKTOP_SESSION`. No E2E possible.
- Issues verified + closed: **none** — all 5 status:done (#786 #788 #807 #840 #843) still partial-verified, blocked on #863. No new comments posted (would be duplicate noise).
- Regression (Phase 5): TC-0046 PASS (consec 26); TC-0052 / TC-0053 partial / TC-0054 / TC-0055 / TC-0057 / TC-0058 / TC-0059 / TC-0060 all FAIL unchanged (sources #864–#873).
- New issues created: **#874** (bug, P2, from:qa, v0.3.4) — `-j --version` / `-j --help` / `-j <unknown-cmd>` bypass JSON envelope; top-level eager-option twin of #872. Discovered during Accessibility User persona script (env-probe via `naturo -j --version`).
- New test cases created: **TC-0061** (`eager-option-bypasses-json-envelope.yaml`, sources #874).
- Test cases retired: none.
- Total active test cases: ~39 active / 22 retired / 2 blocked.
- Tests run: 151 unit (skipped), 9 CLI-contract regression TCs, ~12 exploratory probes (help-text audit, JSON envelope sweep, exit-code matrix, MCP handshake).

## Status:done queue
- Started: 5
- Verified + closed: 0
- Rejected: 0
- Partial-verify, retained: 5 (no movement since R117)
- **End of round**: 5 (#786, #788, #807, #840, #843) — all still blocked on #863

## Top 3 Risks
1. **#863 (P0 ship gate)** — day 4 since escalation, session still non-interactive. v0.3.2 ship is locked behind this single issue. Console-session QA access remains the unblock.
2. **CLI-contract debt cluster (8 open)** — #864 #865 #866 #867 #869 #871 #872 #873 #874. Recognizable pattern: Click's pre-command handlers (eager options, UsageError, "did you mean", optional-dep prompts) bypass naturo's JSON envelope. A single PR refactoring the root CLI group to honor `-j` everywhere would close most of them.
3. **MCP correctness** — 2 MCP bugs in 4 rounds (#868 silent black PNG, #873 wrong version). MCP layer needs a dedicated correctness pass before AI Agent Builder adoption is comfortable.

## Persona Coverage (rolling)
| Persona | Last round | Findings |
|---------|-----------|----------|
| First-time User (0) | R120 | #867 |
| AI Agent Builder (1) | R121 | #868 |
| Enterprise RPA Dev (2) | R122 | #869 |
| Chinese User (3) | R123 | #870 + #871 |
| Power User (4) | R124 | #872 + #873 |
| **Accessibility User (5)** | **R125** | **#874** |
| Scripter (6) | R118 | #864 #865 #866 |
| Skeptical Evaluator (7) | — | next round |
