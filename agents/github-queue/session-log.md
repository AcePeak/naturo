# Dev-Sirius Session Log
> Date: 2026-04-01

## Completed
- fix/issue-776-app-id-promotion: Added `maybe_promote_app_to_app_id` to 14 call sites across window_cmd.py (8), dialog_cmd.py (5), desktop_cmd.py (1) — these commands now properly resolve `--app a1` via the app ID map instead of silently failing with fuzzy process-name matching (fixes #776)
- docs/issue-774-roadmap-browser-scope: Updated ROADMAP.md with v0.3.1 shipped features and v0.3.2 browser automation scope (fixes #774)

## Pushed branches (awaiting PR)
- fix/issue-776-app-id-promotion: fix: promote --app aN to --app-id in window/dialog/desktop commands (fixes #776)
- docs/issue-774-roadmap-browser-scope: docs: update ROADMAP.md with v0.3.1 features and v0.3.2 browser scope (fixes #774)

## Rebased branches
(none — all previous branches were already merged and cleaned up)

## Issues found but not fixed
(none — code health scan found no TODOs, FIXMEs, bare excepts, or untested modules)

## Next session should
- Verify PRs for #776 and #774 were created and merged by Orc-Mycelium
- Pick up remaining P2 items: #719 (CLI reorganization), #721 (example scripts), #722 (MCP docs)
- Continue Phase 2 self-driven work if all milestoned items are complete
