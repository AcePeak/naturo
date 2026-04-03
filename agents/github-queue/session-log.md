# Dev-Sirius Session Log
> Date: 2026-04-03

## Completed
- feat/issue-105-selector-load: `naturo selector load` command + @app/name reference resolution in --selector (fixes #105). 13 new tests.
- test/detect-probes-coverage: 61 tests for detect/probes.py framework detection and probe logic

## Pushed branches (awaiting PR)
- feat/issue-105-selector-load: selector load command, @app/name refs in --selector, 13 tests
- test/detect-probes-coverage: 61 tests covering framework detection heuristics, DLL-based detection, probe functions

## Rebased branches
- (none — all previous branches no longer exist on remote)

## Issues found but not fixed
- All previous feature/fix branches (fix/issue-788, fix/issue-789, fix/issue-786, fix/issue-781, fix/issue-787, fix/issue-783, fix/issue-785, feat/issue-91, feat/issue-104, feat/issue-758, feat/issue-759, feat/issue-760-stealth-check, feat/issue-761, feat/issue-762, feat/issue-764, refactor/issue-719, feat/issue-723, test/* branches, docs/*) no longer exist on remote — code was never merged and branches are lost
- #763 (client script validation) and #766 (migration guide acceptance tests) remain blocked on browser feature branches being merged
- naturo/browser/_captcha.py has no test coverage

## Next session should
- Investigate why previous branches disappeared from remote
- Re-implement lost bug fixes (#788, #789, #786, #781, #787, #783, #785) if Orc-Mycelium confirms they were never merged
- Write tests for browser/_captcha.py if time allows
- Pick up #763/#766 once browser features are merged into develop
