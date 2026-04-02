# QA Status
Last updated: 2026-04-02 17:17
Current round: 97
Current milestone: v0.3.2

## This Round
- CI Desktop Tests: 5 passed, 1 failed (#777 unicode path), 18 skipped (commit b936aa7). E2E: 9 passed
- Issues verified: none pending
- E2E tests: Calculator (pass), Notepad (pass)
- Regression: 7/10 passed, 0 retired
- New test cases created: TC-0048
- Test cases cleaned up: none
- New issues created: #810
- Total active test cases: ~25
- Tests run: 17+

## Top 3 Risks
1. **MCP stdout pollution (#810)** — AI agents cannot use naturo MCP server without workaround; blocks AI Agent Builder use case
2. **type -E newline drop (#784)** — Multiline text automation broken in keystroke mode; workaround: use --paste
3. **JSON stderr duplication (#783)** — Scripts using `2>&1` pipe get broken JSON; workaround: redirect stderr separately
