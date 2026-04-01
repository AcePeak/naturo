# Open Issues Snapshot — v0.3.2

> Last updated: 2026-04-01 by Orc-Mycelium
> This file is a snapshot for Dev-Sirius when GitHub tools are unavailable.
> Orc-Mycelium updates this periodically.

## Priority Order (work on these first)

### P1 Bugs
- #776 [P1,bug] bug: --app aN (app ID from list apps) silently fails, must use --app-id aN instead

### P1 Tasks
- #581 [P1] QA: Run desktop CI verification after 15-PR bug-fix sprint
- #773 [P1] QA: verify 8 status:done issues before v0.3.2 release

### Status:done (awaiting QA verification, do NOT re-work)
- #702 [P2,status:done] AI vision: improve dedup with text matching + proximity search
- #754 [verified,status:done] feat: add --ai-model/--ai-provider/--ai-api-key CLI params for vision
- #757 [status:done] Human-like mouse motion primitives (has open PR #768)

### Status:in-progress
- #720 [P2,status:in-progress] refactor: split windows/_element.py (1,517 lines)
- #725 [P2,status:in-progress] ops: triage 12 unmilestoned open issues
- #759 [status:in-progress] naturo browser subcommand

### P2 Available (unassigned, no status label)
- #719 [P2] refactor: reorganize CLI commands by domain
- #721 [P2] docs: create working example scripts
- #722 [P2] docs: create dedicated MCP server reference
- #723 [P2] ops: add cost guardrails for scheduled agents
- #726 [P2] docs: record hero GIF for README
- #727 [P2] community: create good-first-issue tasks
- #774 [P2] docs: update ROADMAP.md for browser automation scope

### Browser Automation (from:ace, new scope)
- #758 Chrome profile management
- #760 Anti-detection defaults
- #761 Captcha handling architecture
- #762 Browser wait mechanisms
- #764 iframe support
- #765 Network request interception
- #763 Client script validation (depends on all above)
- #766 Migration guide acceptance tests (depends on all above)

### Large Features (deferred unless time permits)
- #90 Enterprise recording/playback engine
- #91 Enterprise visual regression testing
- #104 Built-in selector templates for Top 20 apps
- #105 User selector management

## Open PRs (need attention)
- PR #768: feat/issue-757-mouse-trajectory — OPEN, check if CI passed
- PR #770: feat/gemini-vision-provider — OPEN, has merge conflict with develop
- PR #771: feat/issue-754-ai-cli-params — OPEN, has merge conflict with develop
- Branch feat/see-cascade-ai-model-params — pushed, NO PR created yet
- Branch fix/issue-752-app-accepts-app-id — pushed, NO PR created yet
- Branch fix/trajectory-and-registry-quality — pushed, NO PR created yet

## Dev-Sirius Instructions
1. Fix P1 bugs first (#776)
2. Rebase conflicting branches onto develop and re-push
3. Write PR requests to `agents/github-queue/pr-requests.md` for any new branches
4. Do NOT re-work status:done issues — those are waiting for QA
