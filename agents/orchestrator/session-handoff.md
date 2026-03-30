# Session Handoff — Orc-Mycelium

> This file preserves context across sessions. Read this on every startup.
> Last updated: 2026-03-30 by Orc-Mycelium

## Who Am I

I am **Orc-Mycelium**, the strategic orchestrator of the naturo project. My role:
- Coordinate Dev-Sirius (dev agent) and QA-Mariana (qa agent)
- Do weekly/daily reviews, create issues, adjust milestones
- Fix CI/infrastructure problems
- Communicate with Ace (the project owner)
- My git identity: `Orc-Mycelium <ace.busy@gmail.com>`

## Current Product State (2026-03-30)

### Version Status
- **v0.3.0**: Released on PyPI (2026-03-26)
- **v0.3.1**: 100% issues closed (59 closed, 0 open) — **ready to release** pending:
  1. Ace's final real-machine verification (started, found issues, Dev fixed them)
  2. NEW: highlight DPI bug still open (see coordinates correct but GDI drawing wrong)
  3. Need to bump version to 0.3.1 in code, tag, publish to PyPI
- **v0.3.2**: 82% (5 open: #104 selector templates, #105 selector mgmt, #412 input strategy refactor, #580 scope decision, #581 desktop CI)
- **v0.3.3**: 14% (Enterprise: Excel/SAP/MinHook/standalone exe)
- **v0.3.4**: 28% (Launch & community)

### Blocking Issues for v0.3.1 Release
- **highlight DPI bug** (NOT YET FILED as GitHub issue — MCP disconnected):
  - `naturo see --app notepad` returns correct coordinates after #613 fix
  - `naturo highlight --app notepad` draws boxes at wrong positions on 4K + 150% DPI
  - Root cause: `bridge/_highlight.py` line 418 uses GDI `Rectangle(hdc, ex, ey, ...)` with screen DC whose DPI coordinate space doesn't match UIA snapshot coordinates
  - Fix: ensure DPI awareness context matches between `see` capture and `highlight` draw
  - Priority: P0, milestone: v0.3.1

### Release Plan
1. Fix highlight DPI bug
2. Ace does final verification on 4K Windows 11 machine
3. Bump version to 0.3.1
4. Tag + publish to PyPI
5. After v0.3.1 release: create `develop` branch, switch all agents/CI to develop, lock main for releases only

## Key Product Decisions (from Ace)

### Architecture
- **naturo is an orchestration/编排 layer** — it should integrate best-of-breed tools (Playwright, Browseruse) for web content rather than reimplementing CDP from scratch
- Same pattern as macOS where naturo wraps Peekaboo CLI
- Auto-detect what's available → use it → fall back gracefully
- User can also force a specific method via `--method`

### Browser Strategy
- UIA for Chrome/Electron framework (address bar, tabs, buttons) ✅ working
- CDP for web content inside Chrome ✅ just shipped (#617)
- For Electron apps like Feishu that block CDP: MinHook injection (v0.3.3 roadmap) or AI Vision fallback
- Consider integrating Playwright/Browseruse as providers in cascade
- **TODO**: Analyze Naturobot Engine's browser capabilities (private repo, couldn't access — need Ace to provide files or open a session with that repo)

### Branch Strategy (agreed, not yet implemented)
- After v0.3.1 release: `main` = stable release = PyPI version
- `develop` = daily development, agents work here
- Feature branches → PR → develop (auto-merge)
- develop → main only on release (tag + PyPI publish)

### Git Identity (implemented)
- `.mailmap` file created for historical remapping
- Dev-Sirius: `Dev-Sirius <ace.busy@gmail.com>`
- QA-Mariana: `QA-Mariana <ace.busy@gmail.com>`
- Orc-Mycelium: `Orc-Mycelium <ace.busy@gmail.com>`
- All agents set git config in their prompt startup
- `agents/dev/status.md` and `agents/qa/status.md` deleted — status tracked via GitHub Issues only

### QA Improvements (from Ace's testing)
- QA ran 27 rounds without catching P0 bugs Ace found in 5 minutes
- Root causes: QA tested on 1080p/100% DPI, single-app foreground, never tested AI Vision
- Added 6 mandatory real-world test cases (TC-0024 to TC-0029)
- QA must change DPI scaling during testing (rotate 100%/125%/150%/200%), restore after
- QA prompt references test case YAML files instead of duplicating steps

## Agent System

### Schedule (Claude Code web UI)
- **Dev-Sirius**: Hourly, repository AcePeak/naturo
- **Daily Review (Orc-Mycelium)**: Daily 09:00, repository AcePeak/naturo
- **QA-Mariana**: GitHub Actions workflow `qa-agent.yml` on self-hosted Windows runner (Ace's desktop)

### Key Prompt Files
- `agents/orchestrator/dev-prompt.md` — Dev agent instructions (schedule copies this)
- `agents/orchestrator/qa-prompt.md` — QA agent instructions
- `agents/orchestrator/review-prompt.md` — Daily review instructions

### CI Architecture
- GitHub Actions `windows-latest`: NO desktop session, `continue-on-error: true`
- `conftest.py` monkeypatch: auto-skip WindowsBackend()/NaturoCore() on CI Windows
- Self-hosted runner `windows-desktop`: real desktop tests (Ace's machine)
- concurrency group per branch to avoid wasted CI minutes

## Recurring Issues & Lessons Learned

### CI Windows DLL Tests
- **Root cause**: GitHub Actions windows-latest has no desktop session
- Tests that call UIA/COM functions hang indefinitely
- **Permanent fix**: conftest.py monkeypatch + continue-on-error: true
- Dev must add `@pytest.mark.desktop` to any test calling WindowsBackend()/NaturoCore()
- Dev must run `ruff check` + `mypy` before creating PR

### DPI Scaling on UWP Apps
- UWP apps (Notepad on Win11) return different coordinates than Win32 apps
- `_ensure_dpi_awareness()` with `SetThreadDpiAwarenessContext` is critical
- Still not fully solved for highlight (GDI draw vs UIA capture mismatch)
- Must test at multiple DPI levels (100%, 125%, 150%, 200%)

### AI Vision
- Anthropic API works but response parsing was broken (JSON in markdown code blocks)
- Coverage estimation was counting empty container Panes as "covered"
- Both fixed in #611 and #609 — needs re-verification on real machine

### External PRs
- Got 3 forks and 2 external PRs (README changes) — likely resume-padding
- Policy: close with polite message pointing to `good first issue` label
- Don't accept low-quality drive-by PRs

## TODO for Next Session

### Immediate
1. **Create GitHub issue**: highlight DPI bug (P0, v0.3.1) — couldn't create because MCP disconnected
2. **Verify Dev-Sirius fixed it** — check if there's a PR for the highlight DPI issue
3. **Ace's final verification** — Ace needs to re-test with latest DLL on 4K machine

### Short-term
4. **Release v0.3.1** — after verification passes
5. **Implement main/develop branch split** — after v0.3.1 tag
6. **v0.3.2 scope decision** — #580 asks whether to ship as-is or split

### Medium-term
7. **Naturobot Engine analysis** — compare browser capabilities with Playwright/Browseruse (need access to private repo)
8. **Playwright/Browseruse integration design** — naturo as orchestration layer
9. **Hero GIF for README** (#47) — #1 factor for GitHub stars
10. **Launch announcements** (#55) — HN/Reddit/Twitter push

## File References

| Purpose | Path |
|---------|------|
| This handoff doc | `agents/orchestrator/session-handoff.md` |
| Agent system design | `.work/reviews/continuous-agent-system.md` |
| Weekly review (first) | `.work/reviews/2026-03-27-weekly-review.md` |
| Dev prompt | `agents/orchestrator/dev-prompt.md` |
| QA prompt | `agents/orchestrator/qa-prompt.md` |
| Review prompt | `agents/orchestrator/review-prompt.md` |
| QA test cases | `agents/qa/testcases/CATALOG.md` |
| Project state | `agents/STATE.md` |
| Rules | `agents/RULES.md` |
| Vision | `agents/VISION.md` |
| Roadmap | `docs/ROADMAP.md` |
