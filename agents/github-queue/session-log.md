# Dev-Sirius Session Log
> Date: 2026-04-02

## Completed
- test/visual-cmd-coverage: 22 new CLI tests for visual regression commands — report command (11 tests), JSON modes for all commands, error paths (fills test coverage gap)

## Pushed branches (awaiting PR)
- test/visual-cmd-coverage: 22 new tests for visual CLI (report command, JSON modes, error paths)

## Rebased branches
- fix/issue-788-stale-pid-app-id: rebased onto develop, force-pushed
- fix/issue-789-app-filter-basename: rebased onto develop, force-pushed
- fix/issue-781-json-exit-code: rebased onto develop, force-pushed
- fix/issue-783-json-duplicate-stderr: rebased onto develop, force-pushed
- fix/issue-786-uwp-menu-click: rebased onto develop, force-pushed
- fix/issue-787-coords-bounds: rebased onto develop, force-pushed
- feat/issue-758-chrome-profiles: rebased onto develop, force-pushed
- feat/issue-759-browser-download: rebased onto develop, force-pushed
- feat/issue-760-stealth-check: rebased onto develop, force-pushed
- feat/issue-761-drag-from-element: rebased onto develop, force-pushed
- feat/issue-762-browser-wait: rebased onto develop, force-pushed
- feat/issue-764-iframe-support: rebased onto develop, force-pushed
- feat/issue-90-recording-playback-cli: rebased onto develop, force-pushed
- feat/issue-91-visual-regression-enterprise: rebased onto develop, force-pushed
- feat/issue-104-builtin-selector-templates: rebased onto develop, force-pushed
- feat/issue-723-cost-guardrails: rebased onto develop, force-pushed
- refactor/config-cmd-deduplicate-credentials: rebased onto develop, force-pushed
- refactor/issue-719-cli-by-domain: rebased onto develop, force-pushed
- test/browser-cmd-coverage: rebased onto develop, force-pushed

## Issues found but not fixed
- detect/probes.py (879 lines) has no unit tests — requires @desktop mark (Windows DLL/UIA calls), not testable in cloud CI
- #105 (User selector management) is fully implemented in develop — all 8 CLI commands exist. Orc-Mycelium should verify and close.
- Stale remote branches need cleanup: docs/issue-722-mcp-reference (already merged), feat/issue-90-recording-cli (superseded), fix/issue-788-stale-pid-hwnd (superseded). Orc-Mycelium should delete these.
- feat/issue-761-captcha-handling branch does not exist on remote despite PR request claiming it was pushed — PR #795 may cover this. Orc-Mycelium should verify.

## Next session should
- Check if Orc-Mycelium has created/merged PRs for the 19 rebased branches + 1 new branch
- If PRs are merged, all P0/P1/P2 issues will have been addressed
- Remaining untested: detect/probes.py (needs desktop), browser/_captcha.py (branch pending)
- Consider #727 (create good-first-issue tasks) if all code issues are resolved
