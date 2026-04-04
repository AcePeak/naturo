# Dev-Sirius Session Log
> Date: 2026-04-04

## Completed
- fix/issue-781-json-exit-code: selector clear, selector export, and visual report now exit non-zero when emitting {"success": false} in both JSON and text modes (fixes #781)
- fix/issue-789-app-filter-basename: ntpath.basename() extraction before --app matching in _resolve_hwnd, _resolve_hwnds, and list-windows --app filter (fixes #789)
- fix/issue-783-json-duplicate-stderr: NullHandler on root logger in JSON mode + verbose/log-level config + WARNING→DEBUG downgrade in _press.py (fixes #783)
- fix/issue-787-coords-bounds: click --coords validates coordinates against screen bounds via GetSystemMetrics (fixes #787)
- fix/issue-788-stale-pid-routing: _is_hwnd_alive() helper with IsWindow() check in _resolve_app_id and _resolve_hwnd (fixes #788)
- fix/issue-785-winui3-uia-probe: rebased onto develop, tests pass (fixes #785)
- fix/issue-786-uwp-menu-click: rebased onto develop, tests pass (fixes #786)

## Pushed branches (awaiting PR)
- fix/issue-781-json-exit-code: 4 new tests (selector clear JSON/text, selector export JSON, visual report JSON)
- fix/issue-789-app-filter-basename: 5 new tests + list-windows basename fix in _list.py
- fix/issue-783-json-duplicate-stderr: 3 new tests (NullHandler install, verbose mode, no log output)
- fix/issue-787-coords-bounds: existing tests pass (remote already had complete fix)
- fix/issue-788-stale-pid-routing: 8 new tests (_is_hwnd_alive, stale/live app-id, passthrough, expired, stale/live hwnd)
- fix/issue-785-winui3-uia-probe: 4 tests (1 skipped), rebased
- fix/issue-786-uwp-menu-click: 4 tests, rebased

## Rebased branches
- fix/issue-785-winui3-uia-probe: rebased onto develop, force-pushed
- fix/issue-786-uwp-menu-click: rebased onto develop, force-pushed

## Issues found but not fixed
- Previous bug-fix branches keep being deleted from remote without being merged — 6th+ session recreating these fixes
- #105 (user selector management) already implemented: save/list/export/import/delete/test/clear all exist on develop
- #763 (client script validation) still blocked on browser PRs being merged
- #766 (migration guide acceptance tests) still blocked on browser PRs being merged
- app_cmd.py (1,416 lines) and _shell.py (1,216 lines) still need split issues

## Next session should
- CRITICAL: Verify Orc-Mycelium creates PRs from all 7 pushed bug-fix branches this time
- If branches are deleted again without PRs, escalate to Ace — the rework cycle is wasting multiple sessions
- Work on #763/#766 if browser PRs resolve
- Check if #105 can be closed (fully implemented already)
- Consider test coverage gaps
