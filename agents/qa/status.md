# QA Status
Last updated: 2026-05-28 01:08
Current round: 121
Current milestone: v0.3.2 (22 open / 88 closed, 80%)

## This Round
- Persona: AI Agent Builder (hour 01 % 8 = 1)
- CI Desktop Tests: skipped (no source-code commits since `.last-ci-sha = cf3e1fd5`; all commits in between are `[skip ci]` QA/Orc reports). `.last-ci-sha` NOT advanced.
- Targeted unit tests for the 5 blocked `status:done` issues: **48 passed** (stale_hwnd / newline / press_focus / capture_popup / click_uwp). Code health unchanged.
- Issues verified + closed: **none** — all 5 status:done still blocked on #863 (round 121 data point posted to #863).
- E2E tests: skipped (no desktop). MCP server probed directly instead — see Phase 4.
- Regression (Phase 5): TC-0041 (consec 31), TC-0046 (consec 22) — pass. TC-0054 (#866), TC-0055 (#867) — fail (unchanged). TC-0052/TC-0053 partial (success branches need desktop).
- New issues created: **#868** (bug, P0, from:qa, silent-failure, v0.3.2) — MCP `capture_screen` returns all-black PNG with `success: true` when desktop not bindable. Discovered during AI Agent Builder simulation.
- New test cases created: **TC-0056** (`regression/mcp-capture-screen-silent-black.yaml`, sources #868).
- Test cases cleaned up: none.
- Total active test cases: 35 active / 22 retired.
- Tests run: 48 unit + 6 active regression TCs + 1 MCP stdio probe (initialize + tools/list + 5 tool calls + decode/file-disk verification).

## Status:done queue
- Started: 5
- Verified + closed: 0
- Rejected: 0
- Partial-verify, retained: 5 (no movement from rounds 117/118/119/120/121)
- **End of round**: 5 (#786, #788, #807, #840, #843) — all blocked on #863

## Top 3 Risks
1. **NEW: #868 P0 silent-failure on MCP capture_screen.** Any AI agent using `capture_screen` while the session can't bind the desktop gets a fake-successful 3840×2160 all-black PNG. PIL extrema `((0,0),(0,0),(0,0))` confirmed both in the base64 payload and the on-disk file. CLI fails cleanly with `NO_DESKTOP_SESSION` in the same session — the MCP path is the regression surface. Likely shares root cause with #863 — recommend paired fix.
2. **#863 5th consecutive round, still ship-gate.** Three workarounds open: console session, accept unit-test evidence + Ace manual smoke, or stand up cloud VM #860 (P1 day 22 unassigned). No mechanism in place to recover desktop binding from inside the QA session.
3. **CLI/MCP contract drift.** This round revealed that the two surfaces don't agree on `NO_DESKTOP_SESSION`. CLI propagates a structured error; MCP `capture_screen` silently fakes success, while MCP `capture_window` / `see_ui_tree` correctly error. The MCP layer needs a single shared precondition check at the tool boundary — both to fix #868 and to harden the AI Agent Builder experience going forward.
