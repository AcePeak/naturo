# Session Handoff — Orc-Mycelium

> This file preserves context across sessions. Read this on every startup.
> Last updated: 2026-04-01 by Orc-Mycelium

## Who Am I

I am **Orc-Mycelium**, the strategic orchestrator of the naturo project. My role:
- Coordinate Dev-Sirius (dev agent) and QA-Mariana (qa agent)
- Do weekly/daily reviews, create issues, adjust milestones
- Fix CI/infrastructure problems
- Communicate with Ace (the project owner)
- My git identity: `Orc-Mycelium <ace.busy@gmail.com>`

## Current Product State (2026-04-01)

### Version Status
- **v0.3.0**: Released on PyPI (2026-03-26)
- **v0.3.1**: Released on PyPI (2026-03-31) — AI vision cascade, DPI fixes, input strategy refactor
- **v0.3.2**: In progress — 20+ issues open, Dev-Sirius actively working. ~50% complete.

### Branch Strategy (ACTIVE since v0.3.1)
- **`main`** = stable release = PyPI version (v0.3.1). Locked for direct push.
- **`develop`** = daily development. All agents work here.
- Feature branches → PR (--base develop) → develop
- `develop` → `main` only on release (tag + PyPI publish)
- Each agent uses its own **git worktree** to avoid conflicts

### Agent Workflow
- **Dev-Sirius**: Creates feature branch → PR → develop. Marks issues `status:done`. NEVER pushes directly to develop or main. NEVER closes issues.
- **QA-Mariana**: Verifies `status:done` issues on desktop. If pass → adds `verified` label AND closes issue. If fail → removes `status:done`, sends back to Dev.
- **Orc-Mycelium**: Reviews, creates issues, adjusts milestones, handles CI/infra. Can push directly to develop for operational changes.

### v0.3.2 Scope
Major features and improvements planned:

| Category | Issues |
|----------|--------|
| **Selector system** | #104 (built-in templates for top 20 apps), #105 (save/load/list/export) |
| **Browser automation** | #758 (Chrome profile mgmt), #759 (`naturo browser` subcommand), #760 (anti-detection defaults), #762 (wait mechanisms) |
| **Input primitives** | #757 (human-like mouse motion: bezier, jitter, overshoot) |
| **Captcha architecture** | #761 (hooks, motion primitives, cookie mgmt, third-party integration) |
| **Validation** | #763 (client script equivalence: 5-phase validation against rpa-client-* patterns) |
| **AI Vision** | #754 (--ai-model/--ai-provider CLI params, model registry, Google Gemini provider) |
| **Recording/Playback** | #90 (enterprise recording engine) |
| **Visual regression** | #91 (screenshot comparison testing) |
| **CLI/Docs** | #719 (CLI reorg), #720 (_element.py split), #721 (examples), #722 (MCP docs), #726 (hero GIF) |
| **Ops** | #723 (agent cost guardrails), #724 (git identity), #725 (issue triage), #727 (good first issues) |

### Key Architecture Decisions (from Ace)

#### Cascade Recognition = Key Differentiator
- UIA + CDP + AI Vision multi-source fusion — no competitor does this
- `cascade/` is now a subpackage (7 modules, split from 1424-line monolith)
- README has dedicated "Cascade Recognition" section
- Proven on Feishu: 705 UIA + 133 vision = 838 total elements

#### AI Vision Model Strategy
- Default should be best model (Opus 4.6), not cheapest
- Model registry with friendly names (user picks `opus-4.6` not `claude-opus-4-6`)
- Support Anthropic, OpenAI, Google Gemini, Ollama
- CLI params `--ai-model` override env vars
- Issue #754 tracks this

#### Browser Automation Strategy
- naturo is an orchestration layer — integrate best tools, not reimplement
- Current: CDP client (688 lines) for Electron/Chrome interaction
- v0.3.2 scope (all tracked with issues):
  - #758: Chrome profile management (create/list/switch/persist)
  - #759: `naturo browser` subcommand (launch/navigate/find/click/type/wait/screenshot)
  - #760: Anti-detection defaults (stealth ON by default, `navigator.webdriver` suppression)
  - #762: Wait mechanisms (DOM events, network idle, element states)
  - #757: Human-like mouse motion (bezier, 4-phase acceleration, jitter, overshoot)
  - #761: Captcha architecture (hooks + motion primitives + cookie management)
  - #763: Validation against 23 rpa-client-* production scripts
- Design principle: anti-detection is default behavior, not opt-in
- Design principle: captcha handling = naturo primitives + user hooks + third-party services
- Browser provider pattern mirrors AI vision provider pattern
- Future: DrissionPage adapter (optional), Playwright (optional)

#### Platform Focus
- **Windows-first** — all development focused here
- Linux/macOS issues (#66, #68, #74, #75, #77, #84, #87, #88) removed from milestones
- Labeled `help wanted` + `good first issue` for external contributors

#### Language Policy
- All code, comments, docs, issues in English
- Chinese app aliases in code are functional (required for Chinese Windows) — keep
- Design docs translated to English (NPM_DISTRIBUTION.md, DESIGN-PRINCIPLES.md done)

## Agent System

### Schedule (Claude Code web UI)
- **Dev-Sirius**: Hourly, starts with `git fetch origin develop && git checkout develop && git pull origin develop`
- **QA-Mariana**: Hourly on self-hosted Windows runner
- **Daily Review (Orc-Mycelium)**: Daily 09:00

All schedules prepend `git fetch origin develop && git checkout develop && git pull origin develop` before reading their prompt file.

### Key Files
| Purpose | Path |
|---------|------|
| This handoff doc | `agents/orchestrator/session-handoff.md` |
| Dev prompt | `agents/orchestrator/dev-prompt.md` |
| QA prompt | `agents/orchestrator/qa-prompt.md` |
| Review prompt | `agents/orchestrator/review-prompt.md` |
| Rules (all agents) | `agents/RULES.md` |
| Project state | `agents/STATE.md` |
| Roadmap | `docs/ROADMAP.md` |
| Config (centralized) | `naturo/config.py` |

### CI Architecture
- **build.yml**: Lint + MyPy, Python tests (3.9/3.12/3.13 matrix on Ubuntu/macOS), C++ DLL build + Windows tests
- **publish.yml**: Triggered by GitHub Release → builds DLL → publishes to PyPI
- **codeql.yml**: Security analysis on push to main/develop
- Python 3.9 has `continue-on-error: true` (pre-existing compat issues)
- Coverage threshold enforced at 70%

## Recurring Issues & Lessons Learned

### Agent Workspace Conflicts (SOLVED)
- **Problem**: Agents shared same working directory, branch switching corrupted each other's work
- **Fix**: Each agent uses dedicated git worktree (`../naturo-dev-sirius`, `../naturo-qa-mariana`)
- **Rule**: RULES.md rule #4 enforces this

### AI Vision Coordinate Pipeline (SOLVED in v0.3.1)
- `capture_window(hwnd)` not `capture_screen()` — targets correct app
- No DPI scaling needed — `PrintWindow` and UIA both in physical pixels
- Auto-detect `[x1,y1,x2,y2]` vs `[x,y,w,h]` bounds format
- Auto-scale from API-downscaled image to actual screenshot dimensions
- UIA tree snapshot for parent lookup — prevents AI nesting
- Tuple `(x,y,w,h)` → JSON array conversion fallback

### Issue Lifecycle (FIXED)
- **Old bug**: `status:done` + `verified` issues stayed open because QA didn't close them
- **Fix**: QA prompt Phase 1 now explicitly runs `gh issue close N` after verification
- **20 issues** were manually closed to clear the backlog

### Post-Release Debt Sweep
- Review prompt has Phase 3.5: after every PyPI release, Orc runs 7-point sweep
- Every finding becomes an issue in the next milestone — zero tolerance for tech debt carry-forward

## TODO for Next Session

### Immediate
1. Check v0.3.2 progress — how many issues still open?
2. Check CI status on develop — is it green?
3. Review any `status:done` issues that QA hasn't verified yet

### Short-term
4. #754 — AI model registry + CLI params (design approved, needs implementation)
5. Browser automation design — `naturo browser` subcommand architecture
6. #104/#105 — Selector system (largest remaining feature in v0.3.2)

### Medium-term
7. #90 Recording/playback engine
8. #91 Visual regression testing
9. #726 Hero GIF for README
10. v0.3.2 release when scope complete
