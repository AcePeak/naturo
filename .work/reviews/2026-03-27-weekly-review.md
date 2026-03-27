# Naturo Weekly Review Report — 2026-03-27

## Executive Summary

Naturo is a Python + C++ desktop automation engine positioned as "Peekaboo for Windows" — giving AI agents eyes and hands on Windows desktops. The project has reached **v0.3.0** with a solid technical foundation, but faces critical gaps in **production readiness**, **community building**, and **cross-platform maturity** before it can achieve its goal of becoming the most-starred open-source UI automation tool.

**Overall Score: 6.5/10** — Strong technical core, but significant work needed on polish, ecosystem, and community.

---

## 1. Architecture Assessment

### Strengths
- **Clean layered architecture**: CLI → Python API → Backend Abstraction → C++ Core. This is textbook good design.
- **Multi-backend framework detection chain** (CDP → UIA → MSAA → JAB → IA2 → Vision) is a genuine differentiator. No competitor does this.
- **ctypes bridge** (`bridge.py`, 55KB) is well-structured, properly handling Unicode repair and JSON serialization.
- **MCP server** (60KB, 82 tools) makes naturo immediately usable by AI agents — this is the biggest competitive advantage.
- **Snapshot system** with persistent screenshots + UI trees is a Peekaboo-aligned design that enables agent decision-making.
- **Post-action verification engine** (`--verify`) addresses the critical "silent failure" problem (#226 lesson).

### Weaknesses
- **Windows backend is monolithic** (`backends/windows.py`, 142KB). This single file handles UIA, MSAA, input, window management, and more. Needs decomposition.
- **Linux backend is a stub** (5KB). No real functionality. Cross-platform story is incomplete.
- **macOS backend wraps Peekaboo CLI** via subprocess — fragile, adds latency, and breaks if Peekaboo API changes.
- **No abstraction for input methods**. SendInput, UIA SetValue, and hardware keyboard (Phys32) are entangled in the backend rather than being pluggable strategies.
- **bridge.py mixes concerns** — data classes, DLL loading, JSON parsing, and error handling all in one 55KB file.

### Recommendations
1. **[P1] Split `windows.py`** into `windows/uia.py`, `windows/msaa.py`, `windows/input.py`, `windows/window.py` (~4 files, 30-40KB each). This is the #1 maintainability risk.
2. **[P2] Extract input strategy pattern** — make SendInput/UIA SetValue/Phys32/CDP input pluggable per-element, not hardcoded chains.
3. **[P2] Pin Peekaboo CLI version** in macOS backend to avoid breaking on upstream changes.

---

## 2. Code Quality Assessment

### Strengths
- Conventional commits consistently used across 400+ commits
- Type hints present on public APIs
- Comprehensive error code system (`errors.py`) with recovery suggestions
- CI enforces version consistency across Python/C++/CMake

### Weaknesses
- **Single contributor** — all 50 recent PRs are from AcePeak. This is a bus factor of 1.
- **Test-to-production ratio is unclear** — 94 test files claim 1,461+ tests, but many are `@pytest.mark.desktop` (skipped on CI). Actual CI coverage is unknown.
- **No linting in CI** — no flake8, ruff, mypy, or black enforcement. Code style is maintained by convention alone.
- **No integration test harness for real apps on CI** — all real app testing requires the compile machine (manual).

### Recommendations
1. **[P0] Add `ruff` linting + `mypy` type checking to CI.** Open source projects get judged on tooling. No linter = amateur perception.
2. **[P1] Add code coverage reporting** (pytest-cov → Codecov badge). Users want to see coverage numbers.
3. **[P1] Create "good first issue" labels** to attract contributors and reduce bus factor.

---

## 3. Issue Backlog Analysis

### Current State
| Metric | Count |
|--------|-------|
| Open Issues | 48 |
| Closed Issues | 197 |
| Close Rate | 80% |
| P0 Issues | 2 (#367 Hybrid tree, #21 Naturobot engine-level) |
| P1 Issues | 2 (#361 Stable ID, #312 Win32+UIA hybrid) |
| P2 Issues | 3 (#382, #313, #168) |
| Task Issues | 37 |
| Enhancement Issues | 27 |

### Issue Distribution by Milestone Area
- **v0.3.x (current)**: 5 issues — P0 #367 (hybrid tree), #312 (hybrid mode), #382 (get --all), #313 (highlight), #361 (stable ID)
- **v0.4.0 (selector + enterprise)**: ~12 issues — selectors (#102-106), Excel (#38), SAP (#39), MinHook (#40), standalone exe (#43)
- **v0.5.0 (Linux)**: ~6 issues — X11 (#66), AT-SPI2 (#68), Wayland (#75), screenshot (#74)
- **v0.6.0 (National OS)**: ~4 issues — DDE (#87), Kylin (#88), recording (#90), regression testing (#91)
- **v1.0 (stable)**: ~5 issues — API stability (#92), Peekaboo collab (#93), community registry (#106)
- **Launch/Growth**: ~14 issues — PyPI (#51), npm (#52), repo public (#54), announcements (#55), videos (#61), etc.

### Critical Observations
1. **⚠️ NONE of the 48 open issues have GitHub milestones assigned.** `agents/STATE.md` references v0.3.1/v0.3.2 milestones, but the actual issues on GitHub have `milestone: null`. This means `gh issue list --milestone "v0.3.1"` returns nothing — the Dev/QA agent workflow described in SOUL.md is broken. **This is the #1 process gap to fix immediately.**
2. **P0 #367 (Hybrid tree)** is the most architecturally ambitious issue — per-node backend selection. This is what differentiates naturo from all competitors. Should be the #1 technical priority.
3. **Launch tasks (#44-#57) are scattered** — no clear milestone assignment. Risk: launch preparation gets deprioritized by feature work.
4. **No "good first issue" labels** — impossible for external contributors to participate.
5. **#21 is a mega-issue** referencing "Naturobot engine-level capabilities" — too broad, needs decomposition into actionable sub-issues.
6. **Zero open bugs labeled `bug`** — all 48 issues are `enhancement` or `task`. Either bug tracking happens elsewhere or bugs are being closed very efficiently.

### Recommendations
1. **[P0] Assign GitHub milestones to all 48 issues NOW.** Without milestones, the Dev/QA agent SOUL.md workflow (`gh issue list --milestone`) is non-functional. Suggested grouping:
   - **v0.3.1**: #367, #312, #382, #313, #361 (current sprint per STATE.md)
   - **v0.3.2**: #102-106, #38-40, #43, #168 (selector + enterprise)
   - **v0.4.0-launch**: #44-57, #61 (open source launch tasks)
   - **v0.5.0**: #66-77, #84 (Linux backend)
   - **v0.6.0**: #87-91 (National OS + enterprise)
   - **v1.0.0**: #92-96, #106 (stable release + ecosystem)
2. **[P0] Decompose #21** into specific, actionable issues with clear acceptance criteria.
3. **[P1] Add "good first issue" labels** to at least 5 issues (#49 README badges, #45 CONTRIBUTING.md, #47 README GIF, #61 demo videos, #46 issue templates).
4. **[P1] Prioritize #367 (hybrid tree)** as the next major feature — this is the technical moat.

---

## 4. CI/CD Assessment

### Strengths
- Multi-stage pipeline: version check → DLL build → Python tests → release
- Cross-platform: Windows (primary) + Ubuntu + macOS
- Automated PyPI publishing on release tags
- npm distribution via `npx naturo mcp`

### Weaknesses
- **No desktop session on CI** — all `@pytest.mark.desktop` tests are skipped. This is the vast majority of meaningful tests.
- **CI cancellations** are a recurring problem (Windows DLL tests timing out / segfaulting without desktop).
- **No linting stage** — code quality is not enforced.
- **No security scanning** (Dependabot, CodeQL, SAST) — required for professional open-source projects.
- **No benchmark tracking** — no way to detect performance regressions.
- **Feishu notification** is internal-only — should also post to GitHub Checks/Status.

### Recommendations
1. **[P0] Add self-hosted Windows runner with desktop session** (#89 is filed but not prioritized). This is the single biggest CI gap — you can't ship a desktop automation tool without testing desktop automation.
2. **[P1] Add ruff + mypy CI stages** — 30 minutes to set up, permanent quality gate.
3. **[P1] Enable Dependabot** for Python dependencies.
4. **[P2] Add CodeQL** for security scanning.
5. **[P2] Performance benchmark stage** — capture `naturo see` and `naturo click` latency per build.

---

## 5. Documentation Assessment

### Strengths
- Excellent internal documentation: ROADMAP, ARCHITECTURE, DECISIONS, DESIGN-PRINCIPLES, TEST_PLAN
- Design docs for major features (UNIFIED_APP_MODEL, UNIFIED_SELECTOR)
- Comprehensive AGENTS.md and per-role SOUL.md files for AI agents
- Good growth strategy (GROWTH.md) with differentiation-based triggers

### Weaknesses
- **README is text-heavy, no visual** — no hero GIF, no demo video, no animated screenshot. This is the #1 factor for GitHub star conversion.
- **No API reference documentation** — users need to read source code to understand the Python API.
- **No tutorials or guides** beyond CLI help — "How to automate Excel with naturo" type content is missing.
- **SUPPORTED_APPS.md** exists but unclear if it's maintained with real test results.
- **README comparison table with Peekaboo** is good but needs a broader comparison (vs PyAutoGUI, pywinauto, AutoIt, WinAppDriver).

### Recommendations
1. **[P0] Hero GIF for README** (#47). This single asset will determine whether visitors star the repo or leave. Notepad automation demo — 15 seconds, clean, impressive.
2. **[P1] Broader comparison table** — add PyAutoGUI, pywinauto, AutoIt, WinAppDriver. Show naturo wins on: MCP support, multi-framework detection, AI agent integration.
3. **[P1] Auto-generate CLI reference docs** from Click command definitions. Publish to GitHub Pages.
4. **[P2] Tutorial series** — "Automate Notepad", "Automate Excel", "Build an AI agent that uses naturo".

---

## 6. Competitive Positioning Assessment

### Competitive Landscape

| Tool | MCP | Multi-Framework | AI Agent Native | Windows | macOS | Linux | Stars |
|------|-----|----------------|----------------|---------|-------|-------|-------|
| **Peekaboo** | ✅ | ✅ (macOS) | ✅ | ❌ | ✅ | ❌ | 5K+ |
| **PyAutoGUI** | ❌ | ❌ (image only) | ❌ | ✅ | ✅ | ✅ | 9K+ |
| **pywinauto** | ❌ | Partial (UIA+Win32) | ❌ | ✅ | ❌ | ❌ | 4K+ |
| **AutoIt** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | N/A |
| **WinAppDriver** | ❌ | ✅ (UIA) | ❌ | ✅ | ❌ | ❌ | 3K+ |
| **Naturo** | ✅ | ✅ (UIA+MSAA+JAB+IA2+CDP+Vision) | ✅ | ✅ | Partial | Stub | 3 |

### Naturo's Unique Advantages
1. **Only tool with MCP server + multi-framework detection** on Windows
2. **AI-agent-first design** — snapshot system, element refs, verification engine
3. **Framework-agnostic** — users don't need to know if it's UIA, MSAA, or CDP
4. **Naturobot commercial engine heritage** — enterprise RPA know-how

### Key Gaps to Fill
1. **Minimal community presence** — repo is public but only 3 stars, 0 forks
2. **No brand recognition** — "Peekaboo for Windows" is the right positioning but needs to be shouted
3. **Linux stub** means "cross-platform" claim is misleading in README
4. **No PyPI download metrics visible** — unclear adoption

### Strategic Recommendations
1. **[P0] Launch announcements ASAP** — repo is already public (3 stars) but has zero promotional presence. Hero GIF + HN/Reddit post is the critical next step.
2. **[P0] Establish the Peekaboo partnership** before someone else does (#93).
3. **[P1] Target the AI agent community first** — MCP/OpenClaw/Claude users. This is a blue ocean, not a crowded RPA market.
4. **[P2] Don't overinvest in Linux** until Windows is bulletproof. The "Peekaboo for Windows" narrative is cleaner without half-baked Linux support.

---

## 7. Release & Version Assessment

### Release History
| Version | Date | Highlights |
|---------|------|-----------|
| v0.1.0 | Mar 21 | Core automation + MCP |
| v0.1.1 | ~Mar 22 | 67 bug fixes |
| v0.2.0 | ~Mar 22 | Removed 12 non-core commands |
| v0.2.1 | ~Mar 23 | Auto-routing + get command |
| v0.3.0 | Mar 27 | Unified App Model |

### Observations
- **Extremely rapid versioning** — 6 releases in 6 days. This suggests the project is in intensive internal development mode.
- **v0.3.0 is the current stable release** on PyPI.
- **v0.3.1 is the immediate priority** with 5 open issues including a P0 regression (#405, now fixed).
- **No tagged releases visible** on GitHub (suggests repo may still be private).

### Recommendations
1. **[P1] Slow down versioning** post-launch. Weekly or bi-weekly releases are sustainable; daily is not.
2. **[P1] Establish a release cadence** — minor releases (x.y.Z) every 2 weeks, feature releases (x.Y.0) every 6-8 weeks.
3. **[P2] Add release notes automation** — generate from conventional commit history.

---

## 8. Agent System Assessment

### Current Agent Infrastructure
- **Two roles**: Dev-Sirius (tech cofounder) and QA-Mariana (quality cofounder)
- **Soul files** define personality, rules, and workflows for each agent
- **run.sh** launches agents via `openclaw agent` command
- **STATE.md** provides shared context for startup
- **RULES.md** defines collaboration protocols and absolute rules

### Strengths
- Well-defined role boundaries (Dev codes, QA tests, External Tester reports)
- Issue-driven workflow with label state machine
- "Cofounder mindset" — agents think like owners, not executors
- Safety rules: never close issues without fixes, never defer without permission

### Weaknesses
- **No orchestrator** — agents run independently without coordination
- **No 24/7 mechanism** — `run.sh` launches once, doesn't loop
- **No conflict resolution** — what happens when Dev and QA disagree on priority?
- **No monitoring/health checks** — if an agent crashes or gets stuck, nobody notices
- **Compile machine dependency** is a single point of failure for QA
- **No cost management** — uncontrolled agent loops could burn API credits

### Recommendations
See Section 9 (Continuous Agent System Design) for the full redesign.

---

## 9. Top 10 Priorities for Next Sprint

| # | Priority | Issue/Task | Rationale |
|---|----------|-----------|-----------|
| 1 | **P0** | Hero GIF for README (#47) | #1 star conversion factor |
| 2 | **P0** | Launch announcements (#55) | Repo is public but nobody knows — need HN/Reddit/Twitter push |
| 3 | **P0** | Ruff + mypy in CI | Professional quality gate |
| 4 | **P0** | Hybrid tree (#367) | Technical moat, key differentiator |
| 5 | **P1** | Self-hosted Windows CI runner (#89) | Can't test desktop automation without desktop |
| 6 | **P1** | Peekaboo partnership (#93) | Positioning and cross-promotion |
| 7 | **P1** | "good first issue" labels | Attract contributors |
| 8 | **P1** | Decompose #21 into actionable issues | Unblock Naturobot engine integration |
| 9 | **P1** | Broader comparison table in README | SEO + differentiation |
| 10 | **P2** | Split windows.py monolith | Maintainability |

---

## 10. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Bus factor = 1 (single contributor) | High | Critical | Attract contributors with good-first-issues, documentation |
| Peekaboo beats naturo to "Windows counterpart" narrative | Medium | High | Establish partnership early (#93) |
| Silent failures in production (#226-type) | Medium | Critical | Verification engine + QA screenshot validation |
| CI can't test real desktop scenarios | Certain | High | Self-hosted runner (#89) |
| Linux stub misleads users | Medium | Medium | Remove Linux from README until v0.5.0, or clearly label "coming soon" |
| Agent costs spiral without guardrails | Medium | Medium | Budget caps, cooldown periods, diminishing-returns detection |

---

## Conclusion

Naturo has a **genuinely strong technical foundation** and a **clear competitive advantage** (MCP + multi-framework detection). The project's biggest risk is not technical — it's **visibility and community building**. The hero GIF, public launch, and Peekaboo partnership are more important than the next 10 bug fixes.

The agent system needs a proper orchestration layer to run 24/7 sustainably. See the companion document `continuous-agent-system.md` for the full design.

---

*Next review: 2026-04-03*
*Reviewer: Claude Code Analysis Agent*
