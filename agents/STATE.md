# Naturo Project Status
> Auto-maintained by Orc-Mycelium. Agents: read on every startup.

## Current Version
v0.3.1 (PyPI + GitHub Release)

## Active Work
Query live data — do not rely on this section for specific issue numbers:
```bash
gh issue list --state open --limit 100 --json milestone,number,title,labels \
  --jq 'group_by(.milestone.title // "backlog") | sort_by(.[0].milestone.title // "z") |
  .[] | "\n### \(.[0].milestone.title // "Backlog")\n\(.[] | "- #\(.number) [\(.labels | map(.name) | join(","))] \(.title)")"'
```

## Milestone Summary (2026-04-02 afternoon)
- **v0.3.2**: Massive progress — 16 PRs merged since last review. Browser automation core (#759 merged), anti-detection (#760 merged), network interception (#765 merged). Selector management (#105) and visual regression testing (#91) shipped. 13 more PRs queued pending GitHub access (chrome profiles, iframe, captcha, wait mechanisms, plus 7 bug fixes). QA-Mariana active again (18 rounds, 6 bugs filed).
- **v0.3.4**: Blocked on v0.3.2.
- **Backlog**: ~63 open issues including Linux platform work, enterprise features, community tasks.
- **Pipeline**: 13 pending PR requests in pr-requests.md awaiting Orc-Mycelium GitHub access. Key pending: #758 chrome profiles, #761 captcha, #762 browser wait, #764 iframe, plus bug fixes #786 #787 #788 #789 #781 #783.

## Agent Roster
- **Dev-Sirius**: Technical cofounder. Reads: dev-prompt.md — highly productive, 3 new features completed today (stealth-check, browser download, drag --from-element)
- **QA-Mariana**: Quality cofounder. Reads: qa-prompt.md — **back online**, 18 QA rounds, 6 bugs filed, regression at 6/16 pass (known issues with pending fixes)
- **Orc-Mycelium**: Strategic orchestrator. Maintains this file. **BLOCKED: no GitHub MCP tools available — cannot create PRs or manage issues**

## Coordination
- Bug tracking: GitHub Issues only
- State flow: status:in-progress -> status:done -> verified -> close
- CI must be green before any merge

## Recent Activity (2026-04-01 to 2026-04-02)
- **16 PRs merged** — continuing the sprint pace
- Features: browser subcommand foundation (#759/#772), anti-detection stealth (#760/#794), network interception (#765/#798), selector management (#105/#805), visual regression testing (#91/#808)
- Bug fixes: app ID resolution in all subcommands (#776/#799), UWP launch PID (#785/#801), type newline drop (#784/#800), trajectory rounding (#778)
- Docs: example scripts (#721/#790), MCP server reference (#722/#791), ROADMAP update (#774/#779), README recording+selector sections (#806)
- Tests: 76 BrowserPage/BrowserElement tests (#803)
- **QA-Mariana reactivated**: 18 rounds (79→96), filed bugs #781 #783 #784 #785 #786 #787 #788 #789
- **Dev-Sirius completed**: stealth-check (#760), browser download (#759), drag --from-element (#761)
- **13 PR requests pending** — Orc-Mycelium lacks GitHub tools to create them

## Code Health
- 42,040 lines Python source, 188 test files
- Large files needing split: `_element.py` (1,473, #720 open), `app_cmd.py` (1,416, needs issue)
- Version consistent: 0.3.1 across pyproject.toml, version.py, PyPI

## Completed Releases
- v0.1.0 — Core features
- v0.1.1 — 67 bug fixes (PyPI)
- v0.2.0 — Unified App Model + DPI
- v0.2.1 — Auto-routing + get command
- v0.3.0 — QA-tested release (PyPI)
- v0.3.1 — Hotfix: CMakeLists.txt + version.cpp sync
