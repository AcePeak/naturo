# QA Status
Last updated: 2026-03-31 18:20
Current round: 68
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 7 passed, 3 failed, 2 xfailed, 1 xpassed (commit 4c7e8df) — failures covered by #683
- Issues verified: none (no status:done issues)
- E2E tests: Notepad (pass), Calculator (pass)
- Regression: 10/11 passed, 1 blocked (TC-0007), 0 retired
- New test cases created: none
- Test cases cleaned up: none
- New issues created: none
- Total active test cases: 22
- Tests run: 11

## Regression Details (Round 68)
| TC | Name | Result |
|----|------|--------|
| TC-0003 | Chinese app name matching | PASS (4) |
| TC-0004 | Calculator E2E | PASS (23) |
| TC-0007 | Click short text | BLOCKED (Chinese locale) |
| TC-0008 | Multi-window targeting | PASS (9) |
| TC-0011 | App filter cross-process | PASS (3) |
| TC-0012 | --pid targeting | PASS (1) — improved from FAIL |
| TC-0014 | Scripted Notepad workflow | PASS (16) |
| TC-0015 | app quit silent failure | PASS (9) |
| TC-0016 | UWP app name matching | PASS (4) |
| TC-0018 | get value unreadable | PASS (8) |
| TC-0030 | type backslash escape | PASS (2) |

## Phase 4 Findings (Enterprise RPA Dev Simulation)
- 10-step workflow completed without failure: launch → see → click → type header → type body → select+copy → delete+undo → verify restore → save dialog → cancel+close
- naturo handles complex multi-step automation reliably
- `app quit` force-closes even with unsaved changes (correct for RPA use cases)
- All hotkeys (Ctrl+A, Ctrl+C, Ctrl+Z, Ctrl+S, Escape) work correctly

## Top 3 Risks
1. **CI tests failing (#683)** — Notepad UIA detection returns only 'vision', 3 tests fail
2. **MCP element_id click broken (#682)** — AI agent workflow blocked, refs not usable
3. **PID targeting fragile for UWP** — TC-0012 passed this round but historically fails with shared ApplicationFrameHost PID
