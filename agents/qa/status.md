# QA Status
Last updated: 2026-05-29 01:13 UTC
Current round: 145
Current milestone: v0.3.2 (27 open / 88 closed)

## This Round
- CI Desktop Tests: skipped (only QA-report commits since last SHA `893209e`; updated to `17aefe6`)
- Issues verified: none — 5 `status:done` (#786/#788/#807/#840/#843) all SendInput-blocked (#863)
- E2E tests: Phase 2 blocked by NO_DESKTOP_SESSION in current QA session
- Persona: AI Agent Builder (hour 01 mod 8 = 1) — MCP probe-driven
- Regression: 7 MCP-relevant cases re-confirmed FAIL on HEAD `17aefe6` (TC-0051, TC-0056, TC-0060, TC-0068, TC-0070, TC-0077, TC-0078); desktop-driven cases skipped
- New test cases created: TC-0085 (`mcp-window-target-param-drift.yaml`)
- Test cases cleaned up: none
- New issues created: #900 (P2, v0.3.4) — MCP window-targeting param name drift (focus_window=`title`, see_ui_tree/capture_window/…=`window_title`, CLI=`--window`)
- Issue comments: #868 (out-of-range `screen_index` silent-black), #885 (read-vs-action guard scope evidence)
- Total active test cases: 64
- Tests run: ~20 MCP tool calls across 3 probe drivers (`.work/qa-r145/`)

## Top 3 Risks
1. #900 + #891 together create silent failures wherever an agent uses the CLI-style key in MCP. Fix at least one of: unify the param name, alias `window`/`title`/`window_title`, or reject unknown keys at the wrapper.
2. #868 + read-side guard gap (#885 cluster) means MCP-using agents receive plausibly-shaped responses while CLI scripts get a hard error in the same environment. Single guard-decorator placement should fix the whole read surface.
3. #890 still failing 100% on HEAD `17aefe6` — one-line wrapper bug (`naturo/mcp/_snapshot.py:165`) but blocks any agent workflow that lists snapshots. Easy win sitting on the queue.
