# QA Status
Last updated: 2026-04-01 03:37
Current round: 74
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 18 passed, 1 failed, 5 skipped (commit b1d91ce); E2E: 8 passed, 2 failed
- Issues verified: #728 (pass), #704 (pass), #737 (pass), #729 (fail)
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 9/9 passed, 0 retired
- New test cases created: TC-0036
- Test cases cleaned up: none
- New issues created: #743
- Total active test cases: 20
- Tests run: 9

## Top 3 Risks
1. **CI test stability** — 2 desktop tests still fail (Notepad window not found), #729 fix not effective
2. **Chinese locale gaps** — app quit with Chinese name broken (#743), potential PID lookup issues in other commands
3. **Unverified backlog** — 7 status:done issues unverified (#730, #717, #714, #713, #712, #702, #660), mostly CI/config items
