# QA Status
Last updated: 2026-03-31 17:26
Current round: 67
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 24 passed, 5 failed, 3 xfailed (commit 7a52fc1)
- Issues verified: none (no status:done issues)
- E2E tests: Notepad (pass), Calculator (pass)
- Regression: 10/12 passed, 1 failed (TC-0012), 1 blocked (TC-0007)
- New test cases created: TC-0033 (MCP click element_id)
- Test cases cleaned up: none
- New issues created: #682 (MCP click element_id), #683 (CI regression)
- Total active test cases: 18
- Tests run: 12

## Regression Details (Round 67)
| TC | Name | Result |
|----|------|--------|
| TC-0003 | Chinese app name matching | PASS (3) |
| TC-0004 | Calculator E2E | PASS (22) |
| TC-0007 | Click short text | BLOCKED (Chinese locale) |
| TC-0008 | Multi-window targeting | PASS (8) |
| TC-0010 | MCP agent workflow | PASS (21) |
| TC-0012 | --pid targeting | FAIL (UWP shared PID) |
| TC-0015 | app quit silent failure | PASS (8) |
| TC-0016 | UWP app name matching | PASS (3) |
| TC-0018 | get value unreadable | PASS (7) |
| TC-0023 | MCP launch missing PID | PASS (2) |
| TC-0030 | type backslash escape | PASS (1) — previously failing, now fixed |
| TC-0031 | Notepad menu click | PASS (1) |
| TC-0033 | MCP click element_id | FAIL (0) — NEW |

## Phase 4 Findings (AI Agent Builder Simulation)
- MCP server starts and accepts JSON-RPC requests correctly
- tools/list returns 64 tools with proper schemas
- type_text, list_windows work end-to-end via MCP
- **BUG #682**: click by element_id fails — see_ui_tree refs not usable in click tool within MCP session
- Coordinate-based clicking works as workaround but defeats purpose of element tree

## Top 3 Risks
1. **MCP element_id click broken (#682)** — core AI agent workflow broken, any agent builder hits this immediately
2. **CI tests regressing (#683)** — 5 tests failing including 2 previously fixed regressions
3. **PID targeting unreliable for UWP apps** — ApplicationFrameHost.exe hosts multiple UWP apps under one PID
