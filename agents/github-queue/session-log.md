# Dev-Sirius Session Log
> Date: 2026-04-01

## Completed
- feat/issue-758-chrome-profiles: Chrome profile management — launcher, profile CRUD, CLI (fixes #758)
  - `_launcher.py`: Chrome auto-discovery (Win/Mac/Linux), profile dirs, ChromeProcess wrapper with CDP health check
  - CLI: `browser launch` (--profile, --headless, --chrome-path, --extra-args), `browser profiles`, `browser profile-delete`
  - 53 new tests, ruff clean
  - Branch recreated (previous version was lost from remote), force-pushed
- feat/issue-760-anti-detection: Anti-detection defaults — stealth flags + JS patches (fixes #760)
  - `_stealth.py`: 7 Chrome flags + 6 JS patches (webdriver, plugins, languages, permissions, chrome.runtime, WebGL)
  - CLI: `browser stealth`, `browser stealth-flags`
  - 22 new tests, ruff clean
  - Branch recreated (previous version was lost from remote), force-pushed
- feat/issue-764-iframe-support: iframe support — frame listing, context switching (fixes #764)
  - BrowserPage: `frames()`, `frame(selector)`, `parent_frame()`, `main_frame()` with nested frame stack
  - `_resolve_element` / `_resolve_elements` now pass `contextId` when inside an iframe
  - CLI: `browser frames`
  - 20 new tests, ruff clean
  - New feature (not a recreation)

## Pushed branches (awaiting PR)
- feat/issue-758-chrome-profiles: Chrome profile management (fixes #758)
- feat/issue-760-anti-detection: Anti-detection defaults (fixes #760)
- feat/issue-764-iframe-support: iframe support (fixes #764)

## Rebased branches
- None (no stale branches found that needed rebasing)

## Issues found but not fixed
- 5 previously pushed branches still missing from remote (work lost): refactor/config-cmd-deduplicate-credentials, docs/issue-721-example-scripts, docs/issue-722-mcp-server-reference, refactor/issue-719-cli-by-domain, feat/issue-762-browser-wait-mechanisms — these need to be recreated
- navigate() still uses private _wait_for_network_idle internally

## Next session should
- Recreate feat/issue-762-browser-wait-mechanisms (wait_for_navigation, wait_for_url, wait_for_function, wait_for_network_idle)
- Implement #761 (captcha handling architecture) — design pattern for pluggable solvers
- Implement #765 (network request interception) — CDP Network domain wrappers
- Investigate whether refactor/issue-719-cli-by-domain and docs branches should be recreated or deprioritized
