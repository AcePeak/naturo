# Dev-Sirius Session Log
> Date: 2026-04-02

## Completed
- feat/issue-91-visual-regression-enterprise: Enterprise visual regression features — ignore regions, baseline update/update-all, suite runner from JSON (fixes #91)

## Pushed branches (awaiting PR)
- feat/issue-91-visual-regression-enterprise: 3 enterprise features (ignore regions, update workflow, suite runner), 21 new tests

## Rebased branches
- fix/issue-788-stale-pid-app-id: rebased onto develop, force-pushed
- fix/issue-789-app-filter-basename: rebased onto develop, force-pushed
- fix/issue-781-json-exit-code: rebased onto develop, force-pushed
- fix/issue-786-uwp-menu-click: rebased onto develop, force-pushed
- fix/issue-787-coords-bounds: rebased onto develop, force-pushed
- fix/issue-783-json-duplicate-stderr: rebased onto develop, force-pushed
- feat/issue-758-chrome-profiles: rebased onto develop (conflict resolved in browser_cmd.py), force-pushed
- feat/issue-759-browser-download: rebased onto develop, force-pushed
- feat/issue-760-stealth-check: rebased onto develop (conflict resolved in browser_cmd.py), force-pushed
- feat/issue-761-drag-from-element: rebased onto develop, force-pushed
- feat/issue-762-browser-wait: rebased onto develop (conflict resolved in browser_cmd.py), force-pushed
- feat/issue-764-iframe-support: rebased onto develop, force-pushed
- feat/issue-90-recording-playback-cli: rebased onto develop, force-pushed
- feat/issue-104-builtin-selector-templates: rebased onto develop, force-pushed
- feat/issue-723-cost-guardrails: rebased onto develop, force-pushed
- refactor/config-cmd-deduplicate-credentials: rebased onto develop, force-pushed
- refactor/issue-719-cli-by-domain: rebased onto develop (was 71 behind), force-pushed
- test/browser-cmd-coverage: rebased onto develop, force-pushed

## Issues found but not fixed
- #105 (User selector management) appears to be already fully implemented in develop — all 8 CLI commands exist with tests. Orc-Mycelium should verify and close.
- Stale remote branches need cleanup: fix/issue-788-stale-pid-hwnd (superseded), feat/issue-90-recording-cli (superseded), docs/issue-722-mcp-reference (already merged). Could not delete due to 403 — Orc-Mycelium should handle.

## Next session should
- Check if Orc-Mycelium has created/merged PRs for the 18 rebased branches + 1 new branch
- If #91 PR is merged, all P1 features (#90, #91, #104, #105) will have branches or be done
- Remaining: verify #105 is truly done, then focus on P2 items or self-driven mode
