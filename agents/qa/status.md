# QA Status
Last updated: 2026-04-01 01:30
Current round: 74
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 12 passed, 4 failed (known #729), 18 skipped, 3 xfailed (commit 390f788)
- Issues verified: #712 (blocked — PR #733 not merged)
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 16/18 passed, 1 retired (TC-0024)
- New test cases created: TC-0036 (MCP see_ui_tree empty elements)
- Test cases cleaned up: TC-0024 retired (#608 closed, 5 passes)
- New issues created: #737
- Total active test cases: 20
- Tests run: 21

## Top 3 Risks
1. **MCP/CLI parity gap** (#737) — MCP see_ui_tree returns 0 elements when CLI returns 178. Blocks AI agent builders from using MCP for UI inspection.
2. **Chinese filepath capture** (#728) — naturo capture fails with Unicode paths. Affects Chinese/CJK users.
3. **CI Notepad discovery** (#729) — 4 CI tests fail because app launch notepad can't find the window. Blocks automated CI validation.
