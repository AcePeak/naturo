# QA Status
Last updated: 2026-05-29 02:10 UTC
Current round: 146
Current milestone: v0.3.2 (29 open / 89 closed; v0.3.4 = 46 open / 8 closed)

## This Round
- CI Desktop Tests: skipped (no new code commits since last SHA `17aefe6`; only QA-report commits since)
- Issues verified: none — 5 `status:done` (#786/#788/#807/#840/#843) all SendInput-blocked (#863)
- E2E tests: Phase 2 desktop blocked by NO_DESKTOP_SESSION; MCP 62-tool sweep instead
- Persona: Enterprise RPA Dev (hour 02 mod 8 = 2)
- Regression: 12 MCP-relevant cases re-confirmed FAIL on HEAD `de03499` (TC-0051, TC-0056, TC-0060, TC-0062, TC-0065, TC-0068, TC-0069, TC-0070, TC-0077, TC-0078, TC-0079, TC-0085); desktop-driven cases skipped
- New test cases created: TC-0086 (`mcp-app-inspect-bogus-pid-silent.yaml`)
- Test cases refined: TC-0085 (matrix corrected — `wait_for_window` in Group A, `menu_inspect` has no title-key)
- Test cases cleaned up: none
- New issues created: **#901 (P1, v0.3.4, silent-failure)** — MCP `app_inspect` accepts non-existent PIDs and returns success:true with empty exe/app + fabricated win32+vision fallback
- Issue comments: #900 (corrected window-target matrix), #893 (MCP `wait_until_gone` analogue), #885 (`menu_inspect` + `tray_list` cluster additions)
- Total active test cases: 65
- Tests run: ~50 MCP tool calls across 3 probe drivers (`.work/qa-r146/`)

## Top 3 Risks
1. #901 widens the silent-failure surface beyond #885's NO_DESKTOP_SESSION middleware scope — process-validation gaps and desktop-binding gaps share the same agent-impact class (success:true + empty/fabricated payload) but need separate fix locations. Worth deciding whether an "agent contract integrity" sweep across the MCP wrapper layer is needed in addition to #885's middleware.
2. `menu_inspect` and `tray_list` MCP wrappers now confirmed in #885's silent-failure cluster scope (CLI counterparts already guarded). Without an `(cli_command, mcp_tool)` parity audit, future MCP tools risk reintroducing the same gap.
3. 5 SendInput-blocked `status:done` (#786, #788, #807, #840, #843) remain unverified. Console-session QA pass is the only path forward; restructured ship gate cannot close without it.
