# QA Status
Last updated: 2026-04-02 02:18
Current round: 85
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 5 passed, 1 failed (known #777), 18 skipped (commit c558ae8)
- CI E2E Tests: 9 passed, 2 xfailed, 2 xpassed
- Issues verified: none pending
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 8/8 passed, 0 retired
- New test cases created: TC-0042 (type -E newline drop, #784)
- Test cases cleaned up: none
- New issues created: #784 (type -E drops newlines)
- Total active test cases: 24
- Tests run: 8 regression + 2 E2E + exploratory suite

## Top 3 Risks
1. **#784: type -E silently drops newlines** — Enterprise RPA workflows need multiline typing via keystroke sim. Silent data loss is severe for scripting.
2. **CI Unicode DLL failure (#777)** — naturo_core.dll capture_screen still fails with Unicode paths in CI test. CLI workaround works via Python PIL fallback.
3. **v0.3.2 scope (27 open issues)** — Browser automation (#758-#766), AI registry, plus original bug fixes. Risk of delayed release.
