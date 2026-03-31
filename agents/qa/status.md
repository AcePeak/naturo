# QA Status
Last updated: 2026-03-31 12:29 UTC (Round 29)
Current round: 29
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 4 passed, 1 failed (timeout), 17 skipped, 1 xpass (commit a7ba5c1)
- CI E2E Tests: 7 passed, 3 failed, 2 xfail, 1 xpass (commit a7ba5c1)
- Issues verified: #651 (pass)
- E2E tests: Notepad (pass, menu click fail), Calculator (pass)
- Regression: 13/19 passed, 2 failed, 4 skipped
- New test cases created: TC-0031, TC-0032
- Test cases cleaned up: none
- New issues created: #671, #672
- Total active test cases: 21
- Tests run: 19

## Regression Details (Round 29)
| TC | Name | Result |
|----|------|--------|
| TC-0003 | Chinese app name matching | PASS |
| TC-0004 | Calculator E2E | PASS |
| TC-0007 | Click short text | SKIP (Chinese locale) |
| TC-0008 | Multi-window targeting | PASS |
| TC-0010 | MCP agent workflow | PASS (partial) |
| TC-0011 | App filter cross-process | PASS |
| TC-0012 | --pid targeting | FAIL |
| TC-0014 | Scripted Notepad workflow | PASS |
| TC-0015 | app quit silent failure | PASS |
| TC-0016 | UWP app name matching | PASS |
| TC-0018 | get value unreadable | PASS |
| TC-0023 | MCP launch missing PID | PASS |
| TC-0024 | Click background window | PASS |
| TC-0025 | DPI coordinate verification | PASS (baseline) |
| TC-0026 | AI Vision fill-gaps | SKIP (no API key) |
| TC-0027 | AI Vision coverage | SKIP (no API key) |
| TC-0028 | UWP multi-tab quit | PASS |
| TC-0029 | Hybrid mode enrichment | SKIP (no Electron) |
| TC-0030 | type backslash escape | FAIL |

## Phase 4 Findings (Power User Simulation)
- **8 apps open on desktop**: Calculator, 2x Explorer, 3x Terminal, Settings, Program Manager
- **--app filter precision**: Correctly targets apps by process name, fails to target by window title
- **BUG #671**: Cannot target specific window by title when multiple windows of same process exist
- **BUG #672**: Click eN on UWP Notepad menu items misses target (File menu doesn't open)
- **Rapid see calls**: ~4.7s each — functional but slow for power users doing rapid automation

## Top 3 Risks
1. **PID targeting broken for UWP apps** (TC-0012) — all UWP share ApplicationFrameHost.exe PID
2. **type command corrupts Windows paths** (TC-0030) — backslash escape sequences break file paths
3. **Element click targeting on UWP menus** (#672) — coordinates from see tree don't produce expected clicks
