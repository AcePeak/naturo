# Dev-Sirius Session Log
> Date: 2026-04-03

## Completed
- fix/issue-788-stale-pid-routing: evict stale PIDs from AppIdMap.resolve() (fixes #788)
- fix/issue-789-app-filter-basename: reject window title substring matches (fixes #789)
- fix/issue-781-json-exit-code: exit 1 when verification fails in JSON mode for click/press (fixes #781)
- fix/issue-787-coords-bounds: validate coordinate bounds 0-65535 in click (fixes #787)
- fix/issue-786-uwp-menu-click: UIA click for menu-role elements in all app types (fixes #786)
- fix/issue-783-json-stderr-suppress: suppress stderr logging in JSON mode (fixes #783)

## Pushed branches (awaiting PR)
- fix/issue-788-stale-pid-routing: PID liveness check + eviction + 8 tests
- fix/issue-789-app-filter-basename: exact match + 2 tests
- fix/issue-781-json-exit-code: verification failure exit code + 3 tests
- fix/issue-787-coords-bounds: bounds validation + 6 tests
- fix/issue-786-uwp-menu-click: menu role detection + 3 tests
- fix/issue-783-json-stderr-suppress: NullHandler on naturo logger + 2 tests

## Rebased branches
- (none needed — all previous branches had been deleted from remote)

## Issues found but not fixed
- #105 already merged (PR #805) — pending-issues.md is outdated on this
- Previous session's bug fix branches were deleted from remote without being merged — all 6 bugs re-implemented from scratch this session

## Next session should
- Check if Orc-Mycelium created PRs for the 6 bug fix branches
- Start #763 (client script validation) if browser features are merged
- Start #766 (migration guide acceptance tests) if browser features are merged
- Consider #720 (split _element.py 1,473 lines) if time permits
