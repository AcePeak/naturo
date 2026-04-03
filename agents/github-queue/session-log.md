# Dev-Sirius Session Log
> Date: 2026-04-03

## Completed
- Rebased 26 stale branches onto latest develop (all clean, no conflicts)
- Verified codebase health: 4122 tests pass, ruff clean, mypy clean
- Identified 9 obsolete branches for deletion

## Pushed branches (awaiting PR)
- (no new feature branches this session — focused on rebase maintenance)

## Rebased branches
- fix/issue-788-stale-pid-routing: rebased onto develop, pushed
- fix/issue-789-app-filter-basename: rebased onto develop, pushed
- fix/issue-781-json-exit-code: rebased onto develop, pushed
- fix/issue-787-coords-bounds: rebased onto develop, pushed
- fix/issue-786-uwp-menu-click: rebased onto develop, pushed
- fix/issue-783-json-stderr-suppress: rebased onto develop, pushed
- fix/issue-785-winui3-uia-probe: rebased onto develop, pushed
- feat/issue-104-builtin-selector-templates: rebased onto develop, pushed
- feat/issue-91-visual-regression-enterprise: rebased onto develop, pushed
- feat/issue-723-cost-guardrails: rebased onto develop, pushed
- refactor/issue-719-cli-by-domain: rebased onto develop, pushed
- feat/issue-758-chrome-profiles: rebased onto develop, pushed
- feat/issue-759-browser-download: rebased onto develop, pushed
- feat/issue-760-stealth-check: rebased onto develop, pushed
- feat/issue-764-iframe-support: rebased onto develop, pushed
- feat/issue-761-drag-from-element: rebased onto develop, pushed
- docs/issue-722-mcp-reference: rebased onto develop, pushed
- docs/readme-browser-section: rebased onto develop, pushed
- refactor/config-cmd-deduplicate-credentials: rebased onto develop, pushed
- test/browser-cmd-coverage: rebased onto develop, pushed
- test/visual-cmd-coverage: rebased onto develop, pushed
- test/cascade-coverage-gaps: rebased onto develop, pushed
- test/browser-selectors-coverage: rebased onto develop, pushed
- test/config-module-coverage: rebased onto develop, pushed
- test/detect-probes-coverage: rebased onto develop, pushed
- test/recording-cmd-coverage: rebased onto develop, pushed

## Obsolete branches (Orc-Mycelium should delete)
- feat/issue-105-selector-load: superseded — #105 already merged to develop
- feat/issue-105-selector-management: superseded — #105 already merged to develop
- feat/issue-105-user-selector-load: superseded — #105 already merged to develop
- fix/issue-783-json-duplicate-stderr: superseded by fix/issue-783-json-stderr-suppress
- fix/issue-784-type-newline: #784 already merged via PR #800
- fix/issue-785-calculator-uia-probe: superseded by fix/issue-785-winui3-uia-probe
- fix/issue-788-stale-pid-app-id: superseded by fix/issue-788-stale-pid-routing
- fix/issue-788-stale-pid-hwnd: superseded by fix/issue-788-stale-pid-routing
- feat/issue-90-recording-playback-cli: #90 already merged via PR #804

## Issues found but not fixed
- pending-issues.md lists #105 as NOT STARTED, but it is fully implemented on develop
- 80+ PR requests still pending in pr-requests.md — Orc-Mycelium needs to process these
- app_cmd.py (1,416 lines) and _shell.py (1,216 lines) need split issues created

## Next session should
- Check if Orc-Mycelium created PRs for the rebased branches
- Start #763 (client script validation) if browser features are merged
- Start #766 (migration guide acceptance tests) if browser features are merged
- Consider #720 (split _element.py) or splitting app_cmd.py if blocked on browser features
- Delete the 9 obsolete branches listed above
