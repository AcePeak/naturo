# QA Status
Last updated: 2026-04-01 06:24
Current round: 75
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 5 passed, 2 failed, 18 skipped (commit c439d87); E2E: 8 passed, 2 failed
- Issues verified: #743 (pass), #715 (pass), #714 (pass), #729 (partial)
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 8/8 passed, 0 retired
- New test cases created: none
- Test cases cleaned up: none
- New issues created: none
- Total active test cases: 21
- Tests run: 20

## Top 3 Risks
1. **CI test flakiness** — zombie UWP Notepad processes cause 2 intermittent test failures (#729)
2. **AI vision untestable** — no API key on runner, cannot verify cascade dedup (#702)
3. **Scripter UX** — nested JSON tree output from `see -j` is unintuitive for automation scripts
