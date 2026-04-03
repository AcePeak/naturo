# Dev-Sirius Session Log
> Date: 2026-04-03

## Completed
- test/recording-cmd-coverage: 75 tests for recording CLI and engine (recording_cmd.py, recording.py)

## Pushed branches (awaiting PR)
- test/recording-cmd-coverage: comprehensive test coverage for record start/stop/play/list/show/delete/export

## Rebased branches
- fix/issue-781-json-exit-code: rebased onto develop, pushed
- fix/issue-783-json-duplicate-stderr: rebased onto develop, pushed
- fix/issue-785-winui3-uia-probe: rebased onto develop, pushed
- fix/issue-786-uwp-menu-click: rebased onto develop, pushed
- fix/issue-787-coords-bounds: rebased onto develop, pushed
- fix/issue-788-stale-pid-routing: rebased onto develop, pushed
- fix/issue-789-app-filter-basename: rebased onto develop, pushed
- feat/issue-105-user-selector-load: rebased onto develop, pushed

## Issues found but not fixed
- #763 (client script validation) and #766 (migration guide acceptance tests) are blocked on browser feature branches being merged
- naturo/detect/probes.py (879 lines) has no test coverage and no existing branch covering it
- naturo/browser/_captcha.py has no test coverage

## Next session should
- Check if Orc-Mycelium created PRs for all rebased branches and test/recording-cmd-coverage
- Work on probes.py test coverage if browser merges are still blocked
- Pick up #763/#766 once browser features are merged into develop
