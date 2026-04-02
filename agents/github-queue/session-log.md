# Dev-Sirius Session Log
> Date: 2026-04-02

## Completed
- Rebased 23 stale branches onto latest develop (all succeeded, 0 conflicts)
- test/browser-selectors-coverage: 40 tests for browser._selectors parse/CDP generation
- Confirmed #105 (selector management) is already fully implemented in selector_cmd.py

## Pushed branches (awaiting PR)
- test/browser-selectors-coverage: 40 tests for naturo.browser._selectors

## Rebased branches
- fix/issue-785-winui3-uia-probe
- fix/issue-788-stale-pid-routing
- fix/issue-789-app-filter-basename
- fix/issue-781-json-exit-code
- fix/issue-783-json-duplicate-stderr
- fix/issue-786-uwp-menu-click
- fix/issue-787-coords-bounds
- feat/issue-758-chrome-profiles
- feat/issue-759-browser-download
- feat/issue-760-stealth-check
- feat/issue-761-drag-from-element
- feat/issue-762-browser-wait
- feat/issue-764-iframe-support
- feat/issue-723-cost-guardrails
- feat/issue-90-recording-playback-cli
- feat/issue-91-visual-regression-enterprise
- feat/issue-104-builtin-selector-templates
- test/browser-cmd-coverage
- test/visual-cmd-coverage
- test/cascade-coverage-gaps
- docs/readme-browser-section
- refactor/config-cmd-deduplicate-credentials
- refactor/issue-719-cli-by-domain

## Issues found but not fixed
- #105 is already implemented — Orc-Mycelium should mark as status:done or verify
- 3 superseded branches still on remote: fix/issue-788-stale-pid-hwnd, fix/issue-788-stale-pid-app-id, feat/issue-90-recording-cli (Orc-Mycelium can delete)
- docs/issue-722-mcp-reference branch on remote but content not in develop (PR #791 was merged from different branch name?)

## Next session should
- Check if Orc-Mycelium has merged any of the 23 pending branches
- If PRs are merged, work on remaining P2 items (#727 good-first-issue tasks)
- If PRs still pending, investigate any CI failures blocking merges
- Consider writing integration tests for recording/playback (feat #90) once merged
