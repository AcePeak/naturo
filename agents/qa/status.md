# QA Status
Last updated: 2026-05-28 04:11
Current round: 124
Current milestone: v0.3.2 (23 open / 88 closed, 79%)

## This Round
- Persona: Power User (hour 04 % 8 = 4)
- CI Desktop Tests: **skipped** (no new commits since 099c2bb; HEAD 2d2c01a is `[skip ci]` QA report)
- Session degraded further than #863 baseline: no desktop access at all (not just SendInput) — `see/capture/list/type/press/click` all return `NO_DESKTOP_SESSION`. Diagnostic comment posted to #863.
- Targeted unit tests for 5 status:done issues:
  - #807 press routing: **66/66 PASS**
  - #840 + #788 type: **64/64 PASS**
  - #786 UWP menu click: **9/9 PASS**
  - #843 capture popup: **27/27 PASS**
  - #870 Windows-only broken tests: **3 FAIL / 73 PASS** (unchanged — no PR)
- Issues verified + closed: **none** — partial-verify only. All 5 status:done still blocked on #863.
- E2E tests: skipped (no desktop). MCP handshake works (initialize → tools/list returns tool catalog) but found a version bug in serverInfo.
- Regression (Phase 5): TC-0041 PASS (consec 34) **→ RETIRED** (#781 closed); TC-0046 PASS (consec 25); TC-0052/TC-0054/TC-0055/TC-0057/TC-0058 FAIL unchanged.
- New issues created:
  - **#872** (bug, P2, from:qa, v0.3.4) — Click UsageError (unknown option / invalid type) bypasses `-j` JSON envelope across see/click/capture/type/press/list. Cousin of #123 (which fixed only the missing-argument path). Discovered during Power User exploratory.
  - **#873** (bug, P2, from:qa, v0.3.4) — MCP serverInfo.version returns mcp SDK version (1.26.0) instead of naturo version (0.3.1). Discovered during Power User MCP probe.
- Existing issues updated: #863 (today's worsened session diagnostic).
- New test cases created: **TC-0059** (`click-usage-bypasses-json-envelope.yaml`, sources #872), **TC-0060** (`mcp-serverinfo-version-mismatch.yaml`, sources #873).
- Test cases retired: **TC-0041** (consec 34, #781 closed).
- Total active test cases: 38 active / 22 retired / 2 blocked = 60 total (was 59 → +2 added, -1 retired… wait correction: was 36/23 last round per status.md, now 38/22 — accounting is messy due to prior round bookkeeping; trust the catalog counts).
- Tests run: 169 unit (66+64+9+27+3) + 8 regression/exploratory TCs + ~25 exploratory probes including JSON envelope sweep, exit-code sweep, MCP handshake.

## Status:done queue
- Started: 5
- Verified + closed: 0
- Rejected: 0
- Partial-verify, retained: 5 (no movement since rounds 117–123)
- **End of round**: 5 (#786, #788, #807, #840, #843) — all still blocked on #863

## Top 3 Risks
1. **#863 (P0 ship gate)** — day 3 since escalation, *worsened* this round (session can't even read the desktop now). Console-session QA access is the unblock.
2. **CLI contract debt cluster** — 7 open `-j`/CLI consistency bugs from rounds 118–124 (#864 #865 #866 #867 #869 #871 #872). Worth a single cleanup sprint before v0.3.4; otherwise #92 (semver guarantee) cannot land.
3. **MCP correctness** — 2 MCP bugs found in 3 rounds (#868 silent black PNG, #873 wrong version). Indicates the MCP layer needs a dedicated correctness pass before AI Agent Builder adoption is comfortable.

## Persona Coverage (rolling)
| Persona | Last round | Findings |
|---------|-----------|----------|
| First-time User (0) | R120 | #867 (snapshot typo leak) |
| AI Agent Builder (1) | R121 | #868 (MCP capture_screen black PNG) |
| Enterprise RPA Dev (2) | R122 | #869 (deps prompt leaks into -j JSON) |
| Chinese User (3) | R123 | #871 (window-targeting flag matrix) |
| Power User (4) | **R124** | **#872 (Click UsageError bypasses -j) + #873 (MCP serverInfo version)** |
| Accessibility User (5) | — | next |
| Scripter (6) | R118 | #864/#865/#866 (CLI contract trio) |
| Skeptical Evaluator (7) | — | next |
