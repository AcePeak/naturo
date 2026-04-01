# Dev-Sirius Session Log
> Date: 2026-04-01

## Completed
- refactor/config-cmd-deduplicate-credentials: replaced private _CREDENTIALS_PATH, _load_credentials(), _save_credentials() with imports from naturo.config. Removed 31 lines of duplicate code. All 25 tests pass.
- docs/issue-721-example-scripts: 5 working example scripts (notepad_hello, window_capture, ui_inspector, form_filler, agent_demo) + updated examples/README.md (fixes #721)
- docs/issue-722-mcp-server-reference: comprehensive MCP reference doc covering all 58 tools across 11 modules, transport options, error handling, worked example (fixes #722)

## Pushed branches (awaiting PR)
- refactor/config-cmd-deduplicate-credentials: force-pushed clean recreation onto develop
- docs/issue-721-example-scripts: force-pushed clean recreation onto develop
- docs/issue-722-mcp-server-reference: force-pushed clean recreation onto develop

## Rebased branches
- None needed — all previous branches were either merged or lost

## Merged since last session
- fix/issue-776-app-id-promotion (commit 30c9d53) — #776 fixed
- docs/issue-774-roadmap-browser-scope (commit 8c80357) — #774 fixed
- fix/trajectory-and-registry-quality (commit f678381)
- feat/issue-759-browser-subcommand (commit 969dcc3) — #759 fixed

## Issues found but not fixed
- app_cmd.py (1,237 lines) and _shell.py (1,216 lines) are large — no tracking issues exist
- #719 (reorganize CLI commands by domain) is a full-session task, did not start

## Next session should
- Verify 3 pushed branches have PRs created by Orc-Mycelium
- Start #719 (reorganize CLI commands by domain) — large refactor, allocate full session
- If #719 is too large, pick smaller P2 items: #723 (cost guardrails), #727 (good-first-issues)
