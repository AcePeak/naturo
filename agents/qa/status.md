# QA Status
Last updated: 2026-03-29 18:23 UTC (Round 66)
Current round: 66
Current milestone: v0.3.1
Simulated user: Enterprise RPA Dev (persona index 2)

## This Round
- CI Desktop Tests: skipped (no new commits since fda8530)
- Issues verified: #612 (pass), #168 (skip — PR #607 not merged)
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 7/8 passed, 1 failed (TC-0012), 2 retired (TC-0020, TC-0021)
- New test cases created: TC-0030 (type backslash escape)
- Test cases retired: TC-0020 (5 passes, #533 closed), TC-0021 (5 passes, #563 closed)
- New issues created: #619 (type backslash escape), #620 (app quit false failure)
- Total active test cases: 18
- Tests run: 8

## Regression Details (Round 66)
| TC | Name | Result | Consecutive Passes |
|----|------|--------|--------------------|
| TC-0003 | Chinese app name matching | PASS | 1 |
| TC-0004 | Calculator E2E | PASS | 20 |
| TC-0012 | --pid targeting | FAIL | 0 |
| TC-0014 | Scripted Notepad workflow | PASS | 14 |
| TC-0015 | app quit silent failure | PASS | 6 |
| TC-0016 | UWP app name matching | PASS | 1 |
| TC-0020 | click nonexistent app | RETIRED | 5 |
| TC-0021 | type escape sequences | RETIRED | 5 |
| TC-0030 | type backslash escape | FAIL | 0 |

## Phase 4 Findings (Enterprise RPA Dev Simulation)
- **10-step Notepad workflow completed**: launch, inspect, click, type (3 lines), save-as dialog, cancel, cleanup
- **BUG #619**: `naturo type` interprets `\r`, `\n`, `\t` as escape sequences but has no `\\` literal backslash escape. Windows file paths like `C:\Users\test\report.txt` get corrupted. Critical for enterprise RPA.
- **BUG #620**: `app quit` exits 1 with error about parent PID but app IS actually closed. False failure breaks scripted workflows using exit codes.
- **UWP app matching FIXED**: `--app calculator`, `--app calc`, `--app 计算器` all work now (TC-0016 passing after previous failures).
- **Stale element refs are a UX trap**: Using eN refs from a previous `see` call silently clicks wrong targets. Enterprise users doing rapid see->click chains could hit this.

## Top 3 Risks
1. **v0.3.1 has 4 open P0 bugs** (#608, #609, #611, #613) — coordinates wrong on 4K, AI Vision broken, click not foregrounding
2. **type command corrupts Windows paths** (#619) — enterprise users typing file paths will hit this immediately
3. **app quit false failures** (#620) — any scripted workflow using exit codes will break on successful app closes
