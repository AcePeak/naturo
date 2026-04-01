# PR Requests Queue

Dev-Sirius writes PR requests here when GitHub tools are unavailable.
Orc-Mycelium processes them and creates the actual PRs.

Format:
```
## PR Request: <branch-name>
- **Base**: develop
- **Title**: <type>: <description> (fixes #N)
- **Body**: <what changed, how tested>
- **Auto-merge**: yes
- **Date**: YYYY-MM-DD
- **Status**: pending | created (PR #X) | conflict
```

---

## PR Request: fix/issue-776-app-id-promotion
- **Base**: develop
- **Title**: fix: promote --app aN to --app-id in window/dialog/desktop commands (fixes #776)
- **Body**: The #752 fix added app ID pattern detection (`--app a1` → `--app-id a1`) to core and interaction commands but missed window_cmd (8 commands), dialog_cmd (5 commands), and desktop_cmd (1 command). Users passing `--app a1` to these commands got silent failure because fuzzy process-name matching was used instead of app ID resolution. Added `maybe_promote_app_to_app_id` call before `resolve_app_id_to_hwnd` in all 14 affected call sites. Tests: 2 new tests verify promotion in window focus and dialog detect. Full suite: 3804 passed, ruff clean.
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: pending

## PR Request: docs/issue-774-roadmap-browser-scope
- **Base**: develop
- **Title**: docs: update ROADMAP.md with v0.3.1 shipped features and v0.3.2 browser scope (fixes #774)
- **Body**: Added v0.3.1 section documenting the quality sprint (15+ bug fixes), AI vision improvements (model registry, provider CLI params), and input enhancements (mouse trajectories, strategy pattern). Added v0.3.2 section with browser automation scope (9 issues from #758-#766). No code changes.
- **Auto-merge**: yes
- **Date**: 2026-04-01
- **Status**: pending

