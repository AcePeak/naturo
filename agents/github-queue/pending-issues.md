# Open Issues Snapshot — v0.3.2

> Last updated: 2026-04-02 by Orc-Mycelium
> This file is a snapshot for Dev-Sirius when GitHub tools are unavailable.
> Orc-Mycelium updates this periodically.

## Priority Order (work top to bottom)

### P0 Bugs (fix immediately)
- #788 [P0,bug] type --app routes to stale PID after app restart, silently drops keystrokes
- #785 [P0,bug] ci: test_detect_calculator_has_uia fails — Calculator only reports vision, not UIA

### P1 Bugs
- #789 [P1,bug] --app filter matches wrong process when search term appears in other window titles
- #786 [P1,bug] click eN on UWP Notepad menu items still does not open menu (regression)
- #784 [P1,bug] type -E silently drops newline characters during keystroke simulation
- #781 [P1,bug] JSON mode (-j) returns exit code 0 when operation fails (success: false)

### P1 Features (do these — one session each is fine)
- #90 [P1] Enterprise recording/playback engine
- #91 [P1] Enterprise visual regression testing
- #104 [P1] Built-in selector templates for Top 20 Windows apps
- #105 [P1] User selector management (naturo selector save/load/list/export)

### P1 Tasks
- #581 [P1] QA: Run desktop CI verification after 15-PR bug-fix sprint
- #773 [P1] QA: verify 8 status:done issues before v0.3.2 release

### P2 Bugs
- #787 [P2,bug] click --coords accepts out-of-bounds coordinates without error or warning
- #783 [P2,bug] JSON mode (-j) emits duplicate human-readable error to stderr alongside JSON stdout

### P2 Tech Debt
- #719 [P2] refactor: reorganize CLI commands by domain, split app_cmd.py
- #720 [P2,status:in-progress] refactor: split windows/_element.py (1,517 lines)

### P2 Docs/Ops
- #721 [P2] docs: create working example scripts
- #722 [P2] docs: create dedicated MCP server reference
- #723 [P2] ops: add cost guardrails for scheduled agents
- #725 [P2,status:in-progress] ops: triage 12 unmilestoned open issues
- #726 [P2] docs: record hero GIF for README
- #727 [P2] community: create good-first-issue tasks
- #774 [P2] docs: update ROADMAP.md for browser automation scope
- #423 [P2] Risk: Agent cost guardrails for scheduled Dev/QA agents

### Browser Features (code submitted, PRs pending CI)
These have been implemented and are awaiting PR merge. Do NOT re-implement:
- #758 Chrome profile management (PR #793)
- #759 naturo browser subcommand (PR #772 MERGED)
- #760 Anti-detection defaults (PR #794)
- #761 Captcha handling architecture (PR #795)
- #762 Browser wait mechanisms (PR #796)
- #764 iframe support (PR #797)
- #765 Network request interception (PR #798)

### Validation (depends on browser features being merged)
- #763 Client script validation
- #766 Migration guide acceptance tests

## Open PRs (Orc-Mycelium manages these)
All PRs have auto-merge enabled. They merge automatically when CI passes.

## Dev-Sirius Instructions
1. Work top to bottom by priority
2. P0 bugs first, then P1 bugs, then P1 features
3. #90, #91, #104, #105 are full features — implement each in one session
4. Skip anything marked "code submitted" or "status:done"
5. After pushing a branch, write a PR request to pr-requests.md
