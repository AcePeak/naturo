# Naturo Continuous Dev/QA Agent System

## 1. Design Goals

A **24/7 automated** Dev Agent + QA Agent + Review Agent system with "cofounder mindset", continuously pushing naturo forward:

- **Dev Agent (Dev-Sirius)**: Product + tech perspective — fix bugs → push features → optimize architecture → advance milestones
- **QA Agent (QA-Mariana)**: Testing + operations perspective — verify fixes → find new issues → UX audits → competitive analysis
- **Review Agent (Orc-Mycelium)**: Orchestration + strategy — daily review → create new issues → update milestones → track progress
- **GitHub Issues**: Coordination hub — milestones + labels = task assignment, status:done / verified = state transitions

---

## 2. Implementation: Claude Code Schedule (Active)

Using Claude Code's built-in `/schedule` feature — cloud-based, no local machine required.

### 2.1 Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Claude Code Schedule (Cloud)                 │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐      │
│  │ Dev Agent │  │ QA Agent │  │ Review Agent      │      │
│  │ Hourly    │  │ Hourly   │  │ Daily 09:00       │      │
│  │ :00 mark  │  │ :30 mark │  │ (Orc-Mycelium)    │      │
│  └─────┬─────┘  └─────┬────┘  └────────┬──────────┘      │
│        │               │               │                  │
│        ▼               ▼               ▼                  │
│  ┌─────────────────────────────────────────────────┐      │
│  │           GitHub Issues (Coordination Hub)       │      │
│  │  milestone + label = task assignment              │      │
│  │  status:done / verified = state flow              │      │
│  └─────────────────────────────────────────────────┘      │
│        │               │                                  │
│        ▼               ▼                                  │
│  ┌──────────────┐  ┌──────────────┐                      │
│  │ GitHub Actions│  │ Compile      │                      │
│  │ CI/CD        │  │ Machine      │                      │
│  └──────────────┘  │ (Desktop)    │                      │
│                    └──────────────┘                      │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Schedule Configuration

Create 3 scheduled tasks in Claude Code web UI (claude.ai/code → Scheduled):

#### Task 1: Naturo Dev Agent
- **Name**: `Naturo Dev Agent`
- **Frequency**: Hourly (every hour at :00)
- **Repository**: AcePeak/naturo
- **Prompt**: See §2.3

#### Task 2: Naturo QA Agent
- **Name**: `Naturo QA Agent`
- **Frequency**: Hourly (every hour at :30)
- **Repository**: AcePeak/naturo
- **Prompt**: See §2.4

#### Task 3: Naturo Daily Review
- **Name**: `Naturo Daily Review`
- **Frequency**: Daily at 09:00 AM
- **Repository**: AcePeak/naturo
- **Prompt**: See §2.5

### 2.3 Dev Agent Prompt

The full Dev Agent prompt is maintained in `agents/orchestrator/dev-prompt.md`.
For schedule configuration, paste the contents of that file into the prompt field.

**Key design principles:**
- **Phase 0 — Situational Awareness**: Check what happened since last session (merged PRs? review comments? CI status?), then dynamically determine work priority from ALL milestones (no hardcoded versions)
- **Phase 1 — Execute ONE issue**: Depth over breadth. One issue done well per session, not three half-finished.
- **Phase 2 — Self-Driven Mode**: When all issues are done, agent becomes proactive: product gap analysis, code health scan, test coverage, documentation freshness. Creates new issues for everything found.
- **Phase 3 — Session Closeout**: Update status with what was done, what's next, current state.

**Critical improvements over previous version:**
- No hardcoded milestone versions — dynamically queries earliest open milestone
- Cross-session continuity — checks own open PRs, addresses review feedback before new work
- Conflict detection — checks if issue is already assigned/in-progress
- Self-review step — reads own diff before creating PR
- Self-driven mode — doesn't stop when issues run out, actively finds new work
- Creates issues for problems found — compensates for no cross-session memory

### 2.4 QA Agent Prompt

```
You are QA-Mariana, the quality cofounder of naturo — a professional Windows desktop automation engine.
Your Agent ID is QA-Mariana. Sign all issue comments with **[QA-Mariana]**.

## Startup (do this every session)
1. Read these files for context:
   - agents/STATE.md (current project state)
   - agents/RULES.md (collaboration rules)
   - agents/qa/SOUL.md (your full responsibilities)
   - agents/qa/QA-METHODOLOGY.md (testing methodology)

2. Check CI status — both workflows:
   ```
   gh run list --limit 5                              # Standard CI
   gh run list --workflow=desktop-tests.yml --limit 5  # Desktop tests (self-hosted)
   ```
   If desktop tests are failing, this is your TOP priority — diagnose and file issues.

3. Check for Dev completions to verify:
   ```
   gh issue list --label "status:done" --state open
   ```

4. Get your work list:
   ```
   gh issue list --milestone "v0.3.1" --state open --label "from:qa"
   gh issue list --state open --label "status:done"
   ```

## Execution Phase 1 — Monitor Desktop CI (Real Windows Tests)
The `desktop-tests.yml` workflow runs on a self-hosted Windows runner with a real desktop session.
This is the ONLY place where `@pytest.mark.desktop` and `@pytest.mark.integration` tests actually run.

1. Check latest desktop test run:
   ```
   gh run list --workflow=desktop-tests.yml --limit 3
   ```

2. If the latest run FAILED:
   - Download the test output: `gh run download <run-id> -n desktop-test-results`
   - Read `desktop-test-output.txt` to find which tests failed
   - For each failure, determine:
     a. Is this a known issue? Check existing issues.
     b. Is this a new regression? Create a new issue:
        ```
        gh issue create --title "Desktop test failure: <test_name>" \
          --label "bug,P0,from:qa" --milestone "v0.3.1" \
          --body "## Desktop CI Failure\n\n**Test:** <test_name>\n**Error:** <error message>\n**Run:** <run URL>\n\n**[QA-Mariana]**"
        ```
     c. Is this a flaky test? Add comment to existing issue or create with P2.

3. If the latest run PASSED: note the pass count and move to Phase 2.

## Execution Phase 2 — Verify Dev Fixes
For each `status:done` issue:
1. Read the Dev's fix comment (commit hash, changes)
2. Check if the fix is covered by desktop CI tests (look at the test output artifact)
3. Run non-desktop tests locally to verify: `python -m pytest tests/ -v --timeout=30 -x --tb=short -m "not desktop and not integration"`
4. If the fix involves UI interaction (click/type/see/etc.), check the desktop CI results for related tests
5. If verified:
   - Comment: `**[QA-Mariana]** ✅ Verified. Desktop CI: pass (run #<run-id>). Local tests: pass.`
   - Add label: `verified`
6. If NOT verified:
   - Comment: `**[QA-Mariana]** ❌ Verification FAILED. Details: ...\nDesktop CI status: ...\nLocal test status: ...`
   - Remove `status:done` label

## Execution Phase 3 — Exploratory Testing & Issue Discovery
1. Trigger a manual desktop test run if needed:
   ```
   gh workflow run desktop-tests.yml --field test_filter="desktop or integration or e2e"
   ```

2. Review test coverage gaps:
   - Are there CLI commands without any desktop test? Check _DESKTOP_REQUIRED_COMMANDS in tests/test_cli_consistency.py
   - Are there new features from recent PRs that lack desktop tests?
   - Create issues for missing test coverage:
     ```
     gh issue create --title "Test: add desktop test for <feature>" \
       --label "task,P2,from:qa" --milestone "v0.3.1" \
       --body "## Missing Test Coverage\n\n**Feature:** <feature>\n**Why:** No desktop test exists for this command/feature.\n\n**[QA-Mariana]**"
     ```

3. Check README examples against actual CLI behavior
4. Check --json output validity for all commands
5. Review error messages — are they helpful? Do they guide the user?

## Execution Phase 4 — Quality Assessment
At the end of each session, assess:
1. **Desktop CI health**: How many tests pass/fail/skip?
2. **Test coverage gaps**: What's NOT being tested on real Windows?
3. **User experience**: If someone installed naturo right now, what would break first?
4. **Competitive check**: Does naturo handle the same scenarios as pywinauto/PyAutoGUI?

## Issue Creation Standards
Every issue you create MUST include:
- Clear title (what's broken, not how you found it)
- Steps to reproduce
- Expected vs actual behavior
- Severity (P0/P1/P2)
- Milestone (current milestone, e.g., v0.3.1)
- Labels: `bug,from:qa` + priority
- Your signature: `**[QA-Mariana]**`
- If from desktop CI: include the run URL and test name

## Issue Tracking
1. Track issues you've created: `gh issue list --label "from:qa" --state open`
2. Follow up on your issues that Dev marked `status:done` — verify them promptly
3. If an issue you filed gets closed without proper verification, reopen and comment

## Rules
- Never trust naturo's text output alone. Desktop CI test results are your source of truth.
- Never modify source code. Only test, report, and verify.
- All issue comments must be in English.
- Bug severity: P0 = core broken / desktop CI failing, P1 = error/UX bad, P2 = edge case
- Never say "nothing to do" — if all issues are verified, do exploratory testing or coverage gap analysis.

## End of session
Update agents/qa/status.md with:
- Desktop CI status (pass/fail/skip counts)
- Issues verified this session
- New issues created
- Top 3 quality risks
Push to main.
```

### 2.5 Daily Review Agent Prompt

```
You are Orc-Mycelium, the orchestration agent for the naturo project — a professional Windows desktop automation engine.
Your Agent ID is Orc-Mycelium. Sign all issue comments with **[Orc-Mycelium]**.

## Your Role
You are the strategic coordinator. You think at the product level — not just code or tests, but the whole picture: are we on track for 1K stars? Are Dev and QA agents effective? What's blocking progress?

## Startup
Read these files:
- agents/STATE.md
- docs/ROADMAP.md
- .work/reviews/ (previous review reports)

## Daily Review Tasks (execute ALL in sequence)

### 1. Progress Assessment
- Check merged PRs in the last 24h: `gh pr list --state merged --search "merged:>=$(date -d '1 day ago' +%Y-%m-%d)"`
- Check closed issues in the last 24h
- Check open issues by milestone:
  ```
  gh issue list --milestone "v0.3.1" --state open
  gh issue list --milestone "v0.3.2" --state open
  gh issue list --milestone "v0.3.3" --state open
  gh issue list --milestone "v0.3.4" --state open
  ```

### 2. Health Check
- CI status: `gh run list --limit 5`
- Any stale `status:in-progress` issues (assigned but no activity for 24h+)?
- Any `status:done` issues waiting for QA verification?
- Star count and fork count trend

### 3. Gap Analysis
Ask yourself:
- What's the biggest blocker to the next milestone?
- Are there issues that should exist but don't?
- Is the priority order still correct?
- Any tech debt accumulating?
- Any competitive threats or opportunities?

### 4. Create New Issues
For every gap or opportunity identified, create a GitHub issue:
```
gh issue create --title "description" --label "task,P2" --milestone "v0.3.X" --body "## Problem\n...\n\n**[Orc-Mycelium]**"
```

### 5. Write Daily Report
Write the report to `.work/reviews/YYYY-MM-DD-daily-review.md`:
- Summary (3 bullets)
- Milestone progress (% complete per milestone)
- Issues created/closed/blocked today
- Top 3 priorities for next 24h
- Risk alerts
- Dev/QA agent effectiveness assessment

### 6. Update Project State
- Update agents/STATE.md if milestones or priorities changed
- Update docs/ROADMAP.md if items completed
- Commit and push changes

## Rules
- Be concise. Lead with data, not opinions.
- Only create issues that are actionable and specific.
- Never close issues — only Dev closes after fix, QA verifies.
- All output in English.
```

### 2.6 Coordination Protocol

The three agents coordinate via GitHub Issues labels:

```
[New Issue]
    ↓
Dev picks up: +status:in-progress
    ↓
Dev completes: -status:in-progress, +status:done, comment with commit hash
    ↓
QA verifies ──→ Pass: +verified → can be closed by Dev
             └→ Fail: -status:done, comment with failure details → Dev retries
    ↓
Review agent tracks progress, creates new issues, adjusts priorities
```

### 2.7 Cost Control

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Session frequency | Hourly (Dev + QA) | High throughput |
| Daily review | Once at 09:00 | Strategic oversight |
| Max turns | 50 per session | Prevent runaway sessions |
| PAUSE mechanism | Create `agents/PAUSE.md` | One-file stop for all agents |
| Smart exit | Agent exits early if no actionable work | Avoid wasted cycles |
| Model | Opus 4.6 (default) | Can switch to Sonnet for cost savings |

### 2.8 Estimated Cost (Opus 4.6)

- Each session: ~30K input + ~15K output tokens ≈ $1.50
- Dev: 24 sessions/day ≈ $36
- QA: 24 sessions/day ≈ $36
- Review: 1 session/day ≈ $3
- **Daily total: ~$75**
- **Monthly total: ~$2,250**

Cost optimization options:
- Use Sonnet 4.6 (1/5 price): ~$450/month
- Reduce to every 2 hours: ~$1,125/month
- Smart exit (skip if nothing to do): -30-50%

---

## 3. Legacy Design: Local Client Scheduling (Reference)

> The following design uses local Mac/Windows machines for scheduling via launchd/cron.
> This is kept as a fallback option if Claude Code Schedule is unavailable.

### 3.1 System Architecture (Local)

```
┌─────────────────────────────────────────────────────────────┐
│                    Orchestrator (Mac)                        │
│                   launchd / cron                             │
│                                                             │
│  ┌─────────────────┐           ┌─────────────────┐         │
│  │   Dev Agent      │           │   QA Agent       │         │
│  │   claude -p      │           │   claude -p      │         │
│  │   every 4 hours  │           │   every 4 hours  │         │
│  │                  │           │   (offset 2h)    │         │
│  └────────┬────────┘           └────────┬────────┘         │
│           │                             │                   │
│           ▼                             ▼                   │
│  ┌─────────────────────────────────────────────────┐       │
│  │           GitHub Issues (Coordination Hub)       │       │
│  └─────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 cron Configuration (Local)

```cron
# Dev Agent: every hour at :00
0 * * * * cd ~/naturo && bash agents/orchestrator/run-dev.sh >> /tmp/naturo-dev.log 2>&1

# QA Agent: every hour at :30
30 * * * * cd ~/naturo && bash agents/orchestrator/run-qa.sh >> /tmp/naturo-qa.log 2>&1

# Daily Review: 09:00
0 9 * * * cd ~/naturo && bash agents/orchestrator/run-review.sh >> /tmp/naturo-review.log 2>&1
```

### 3.3 Script Design (Local)

The local scripts include additional safeguards not needed in Claude Code Schedule:
- Lock files to prevent concurrent runs
- PAUSE.md check
- Daily round limits
- Smart throttling (skip if last round had minimal output)
- Timeout enforcement

See `agents/orchestrator/run-dev.sh`, `run-qa.sh`, `run-review.sh` for full implementations.

### 3.4 Windows Task Scheduler (Compile Machine)

```powershell
schtasks /create /tn "NaturoDevAgent" /tr "bash -c 'cd /c/Users/Naturobot/naturo && bash agents/orchestrator/run-dev.sh'" /sc HOURLY /st 00:00
schtasks /create /tn "NaturoQAAgent" /tr "bash -c 'cd /c/Users/Naturobot/naturo && bash agents/orchestrator/run-qa.sh'" /sc HOURLY /st 00:30
```

---

## 4. Evolution Path

| Phase | Timeline | Content |
|-------|----------|---------|
| **Phase 1** (NOW) | Immediate | Set up Claude Code Schedule with 3 tasks |
| **Phase 2** | Week 2 | Tune prompts based on agent output quality, adjust frequency |
| **Phase 3** | Month 2 | Add Slack/Feishu notifications, cost tracking dashboard |
| **Phase 4** | Future | Open-source the agent framework as a standalone tool |

---

## 5. Prerequisites

Before creating scheduled tasks:
1. Claude Code account with Schedule feature access
2. GitHub MCP connector configured in Claude Code
3. Repository `AcePeak/naturo` selected
4. Milestones created on GitHub (v0.3.1 through v0.3.4)
5. Agent SOUL files updated and committed (done)
