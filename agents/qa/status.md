# QA Status
Last updated: 2026-04-05 01:14
Current round: 115
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 1 passed, 1 failed (known #841), 8 skipped; E2E: 9 passed, 3 xfailed, 1 xpassed (commit cf3e1fd)
- Issues verified: none (no status:done issues)
- E2E tests: Notepad (pass)
- Regression: 4/7 passed, 3 failed (known open issues)
- New test cases created: TC-0051
- Test cases cleaned up: none
- New issues created: #844
- Total active test cases: 32
- Tests run: 25 scenarios

## Top 3 Risks
1. **Type newline silently dropped** (#840) — Both `-E` and default mode drop newlines. Any automation sending multi-line text is broken. P1 but functionally P0 for real-world use.
2. **Calculator UWP completely invisible** (#841/#785) — app launch reports success but Calculator cannot be seen, clicked, or automated. Blocks any Calculator automation.
3. **MCP debug output on stderr** (#810) — While stdout is clean, stderr pollution may confuse agent frameworks that merge stdout/stderr. Blocks clean AI agent integration.
