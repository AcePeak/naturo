# QA Status
Last updated: 2026-04-02 09:13 UTC
Current round: 91
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 1 failed (#785), 1 passed, 8 skipped (commit 168a98f); E2E: 9 passed, 3 xfailed, 1 xpassed
- Issues verified: none (no status:done issues)
- E2E tests: Notepad (pass), Calculator (fail — #785)
- Regression: 7/10 passed, 3 failed, 1 retired (TC-0023)
- New test cases created: none
- Test cases cleaned up: TC-0023 retired (#575 closed, 6 passes)
- New issues created: none (all bugs already tracked)
- Total active test cases: 23
- Tests run: 10 regression + CI suite + MCP E2E

## Top 3 Risks
1. **Silent failure on stale PID routing** (#788) — type/click report success but target wrong process after app restart. Deal-breaker for AI agent adoption.
2. **Cross-process app filter contamination** (#789) — --app matches Chrome when searching for "notepad" because Chrome tab title contains "notepad". AI agents relying on --app will automate wrong window.
3. **UWP Calculator invisible** (#785) — Calculator launches but is completely invisible to naturo. CI tests also fail. Blocks all Calculator testing.
