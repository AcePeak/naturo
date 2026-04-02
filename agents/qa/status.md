# QA Status
Last updated: 2026-04-02 14:22
Current round: 96
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 139 passed, 4 failed, 1 skipped (commit 16b0024)
- Issues verified: none (no status:done issues)
- E2E tests: Notepad (pass), Calculator (fail — #785)
- Regression: 6/16 passed, 10/16 failed, 0 retired
- New test cases created: none
- Test cases cleaned up: none
- New issues created: none (all findings map to existing open issues)
- Total active test cases: 26
- Tests run: 16

## Top 3 Risks
1. UWP app detection unreliable — Calculator invisible after launch (#785)
2. --app filter matches by title substring — silent wrong-window targeting (#789)
3. JSON mode stderr leak in click/type/press — breaks script piping (#783)
