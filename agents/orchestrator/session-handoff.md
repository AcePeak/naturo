# Session Handoff — Orc-Mycelium

> This file preserves context across sessions. Read this on every startup.
> Last updated: 2026-03-31 (session 2) by Orc-Mycelium

## Who Am I

I am **Orc-Mycelium**, the strategic orchestrator of the naturo project. My role:
- Coordinate Dev-Sirius (dev agent) and QA-Mariana (qa agent)
- Do weekly/daily reviews, create issues, adjust milestones
- Fix CI/infrastructure problems
- Communicate with Ace (the project owner)
- My git identity: `Orc-Mycelium <ace.busy@gmail.com>`

## Current Product State (2026-03-31)

### Version Status
- **v0.3.0**: Released on PyPI (2026-03-26)
- **v0.3.1**: Ready to release pending Ace's final verification
  - highlight DPI bug #662: **FIXED** (merged in #663 + #687)
  - click snapshot misalignment: **FIXED** (merged in #687)
  - AI vision JSON parsing: **IN PROGRESS** (PR #691, needs window-specific capture fix)
- **v0.3.2**: In progress (Dev-Sirius active: #412 input strategy refactor done, test coverage push)
- **v0.3.3**: 14% (Enterprise: Excel/SAP/MinHook/standalone exe)
- **v0.3.4**: 28% (Launch & community)

### What Was Done This Session (2026-03-31)

#### Bugs Fixed & Merged
1. **#662 highlight DPI positioning** (PR #663, merged) — `_draw_gdi_overlay()` with `SetThreadDpiAwarenessContext(-4)`, `flatten_element_tree()` shared with `see`, CLI pre-fetches tree
2. **click snapshot misalignment** (PR #687, merged) — `resolve_ref()` now accepts `app_name` to prevent cross-app snapshot confusion. All interaction commands (click/type/press/scroll/drag/capture) updated
3. **click feedback output** (PR #687, merged) — shows `Clicking e5 (Button "OK") at (120, 220)` before clicking
4. **highlight options parity with see** (PR #687, merged) — added `--visible-only`, `--cascade`, `--fill-gaps`, `--pid`, expanded `--backend` choices
5. **highlight defaults to all elements** (PR #687, merged) — was actionable-only, now shows all like `see`. Use `--actionable-only` to filter
6. **review prompt timestamp** (PR #687, merged) — daily review filename now `YYYY-MM-DD-HHmm`

#### AI Vision (PR #691, open, needs more work)
- `max_tokens` 512→16384 — fixes JSON truncation
- Code fence regex — handles Windows `\r\n`, no trailing newline
- Prompt rewrite — demands leaf elements, pixel-precise bounds, standard roles
- `_merge_ai_into_tree()` — IoU deduplication + smallest-encloser parent grafting
- **BLOCKING BUG FOUND**: cascade auto-capture screenshots the **foreground terminal window** instead of the target app. AI Vision analyzes terminal text instead of the actual app. Needs `capture_screen(hwnd=target)` window-specific capture.
- 13 merge algorithm tests pass

#### Documentation
- **SUPPORTED_APPS.md restructured** — framework-primary + QA evidence + community contributions
- **scripts/generate_compatibility_report.py** — auto-generates validated apps table from QA test cases
- **docs/CONTRIBUTING_APP_RESULTS.md** — community submission guide
- **.github/ISSUE_TEMPLATE/app-test-result.yml** — structured issue form for app testing
- **QA prompt Phase 8 updated** — runs compatibility script after each round
- **docs/case-studies/electron-app-cascade.md** — cascade recognition case study for marketing

### v0.3.1 Released ✅ (2026-03-31)
- Published to PyPI
- AI vision cascade, DPI fixes, input strategy refactor
- `develop` branch created, all agents switched to develop
- `main` = PyPI release only, `develop` = daily development

### Branch Strategy (ACTIVE)
- **`main`** = stable release = PyPI version. Only release merges allowed.
- **`develop`** = daily development. All agents work here.
- Feature branches → PR → `develop` (auto-merge after CI green)
- `develop` → `main` only on release (tag + PyPI publish)

## TODO for Next Session

### Immediate
1. **Fix AI vision window capture** — cascade screenshot must capture the target app window, not foreground terminal. Check `capture_screen()` — does it support `hwnd=` param for window-specific capture? If not, add it.
2. **AI vision DPI coordinate scaling** — AI reports in screenshot pixels (logical), UIA in physical pixels. On 150% DPI these are 1.5x apart. `_merge_ai_into_tree` needs to scale AI coords by `dpi_scale` before IoU comparison.
3. **Merge PR #691** after fixing window capture + DPI scaling

### Short-term
4. **Release v0.3.1** — all blocking issues fixed
5. **Implement main/develop branch split** — after v0.3.1 tag
6. **v0.3.2 scope decision** — #580

### Medium-term
7. **Hero GIF for README** (#47) — could showcase cascade recognition
8. **Launch announcements** (#55) — HN/Reddit/Twitter push
9. **Naturobot Engine analysis** — browser capabilities comparison

## Key Product Decisions (from Ace)

### Cascade Recognition as Key Differentiator
- UIA + CDP + AI Vision multi-source fusion is unique — no competitor does this
- Case study documented in `docs/case-studies/electron-app-cascade.md`
- Should be prominently featured in README, onboarding, marketing
- Algorithm: IoU deduplication → smallest-encloser parent grafting → source tagging

### Documentation Strategy (agreed this session)
- **Framework-primary** compatibility docs (not per-app matrices)
- **QA evidence layer** — auto-generated from test case YAML
- **Community contributions** — fork users submit test results via structured PR/issue
- See `docs/SUPPORTED_APPS.md` for the new structure

### Architecture
- naturo is an orchestration layer — integrates best-of-breed tools
- Auto-detect what's available → use it → fall back gracefully
- `--cascade` for progressive multi-source recognition

## Agent System

### Schedule
- **Dev-Sirius**: Hourly, repository AcePeak/naturo
- **Daily Review (Orc-Mycelium)**: Daily 09:00
- **QA-Mariana**: GitHub Actions on self-hosted Windows runner

### Key Files
| Purpose | Path |
|---------|------|
| This handoff doc | `agents/orchestrator/session-handoff.md` |
| Dev prompt | `agents/orchestrator/dev-prompt.md` |
| QA prompt | `agents/orchestrator/qa-prompt.md` |
| Review prompt | `agents/orchestrator/review-prompt.md` |
| Case study | `docs/case-studies/electron-app-cascade.md` |
| Compatibility docs | `docs/SUPPORTED_APPS.md` |
| Community guide | `docs/CONTRIBUTING_APP_RESULTS.md` |
| Compat script | `scripts/generate_compatibility_report.py` |
| Project state | `agents/STATE.md` |
| Roadmap | `docs/ROADMAP.md` |

## Recurring Issues & Lessons Learned

### AI Vision Window Capture (NEW — 2026-03-31)
- **Root cause**: `capture_screen()` in cascade mode captures the foreground window (terminal), not the target app specified by `--app`
- **Impact**: AI Vision analyzes terminal text instead of the actual app, producing useless elements
- **Fix needed**: Pass `hwnd` of the target app to `capture_screen()` so it captures that specific window
- **Also needed**: Scale AI Vision coordinates by DPI factor before merging with UIA tree

### DPI Scaling
- `SetThreadDpiAwarenessContext(-4)` is critical for all GDI/Win32 operations
- UIA coordinates are in physical pixels (per-monitor DPI aware)
- Screenshots may be in logical pixels — AI Vision coords need scaling
- Must test at 100%, 125%, 150%, 200% DPI
