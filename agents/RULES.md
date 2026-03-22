# Agent 协作规则

## 共享状态
- **项目状态**: `agents/STATE.md` — 只读参考，由闹呢维护
- **Bug 跟踪**: **GitHub Issues** (https://github.com/AcePeak/naturo/issues) — 所有 bug 通过 `gh issue create` 创建和跟踪
- **历史记录**: `.work/bugs.md` — 仅保留历史记录，不再更新
- **外部测试**: `.work/external-test/round-*.md` — 外部测试员写入，Dev/QA 读取

## 角色边界
- **Dev**: 修 bug、写代码、跑 CI。不做测试决策。
- **QA**: 发现 bug、验证修复、质量评估。不改代码。
- **External Tester**: 用户视角测试，写报告。不改代码，不改 bugs.md。
- **闹呢**: 统筹协调、对外沟通、最终决策。

## 外部测试报告处理流程

### QA 职责
每轮启动时，检查 `.work/external-test/` 是否有新的 round 报告：
1. **读取**新的 external test round 报告
2. **评估**每个 ISSUE-E*：
   - 是否已在 GitHub Issues 中（去重）
   - 严重度是否合理（可调整）
   - 是否能复现
3. **转化**为 GitHub Issue：
   - 新问题 → `gh issue create --label "bug,P0,from:external"` 创建 issue
   - 重复问题 → `gh issue comment` 在已有 issue 补充外部视角
   - 不认同的 → 写理由，保留在报告中不删
4. **回写**处理状态到 round 报告末尾：
   ```
   ## 🔄 QA 处理记录
   - ISSUE-E001 → 转为 GitHub Issue #XX (P0)
   - ISSUE-E002 → 已有 Issue #YY，补充外部视角
   - ISSUE-E003 → 不认同，理由：...
   ```
5. **验证修复**后：`gh issue comment` 添加验证结果 + `gh label add verified`

### Dev 职责
- 从 GitHub Issues 获取待修 bug：`gh issue list --label bug --label P0`
- 修完后 `gh issue comment` 说明修复 + commit message 关联 `fixes #N`
- 来源标注 `from:external` 的 bug 优先级可能更高（因为是真实用户视角）

## ⛔ ABSOLUTE RULES — VIOLATION = IMMEDIATE REMOVAL

1. **NEVER close a GitHub Issue without an actual merged commit that fixes it.** If you think it's already fixed, cite the EXACT commit hash. If unsure, leave it open. Closing issues without fixes has caused repeated data loss.
2. **NEVER close issues for future milestones (v0.3.0+).** You can only close issues in the milestone you are currently working on, and only after your fix is committed and CI passes.
3. **NEVER use `gh issue close` in your triage/classification phase.** During triage, you may only comment — not close.

## Git Workflow (MANDATORY)
1. **NEVER push directly to main.** Always use feature branches + PR.
2. Branch naming: `fix/issue-N-short-desc` or `feat/issue-N-short-desc`
3. Workflow:
   ```bash
   git checkout -b fix/issue-109-get-command
   # ... make changes, commit ...
   git push origin fix/issue-109-get-command
   gh pr create --title "fix: description (fixes #N)" --base main
   # Wait for CI to pass, then merge:
   gh pr merge --squash --delete-branch
   ```
4. Only merge PR after CI is green
5. This protects main from broken code

## General Rules
1. Only operate within `~/Ace/naturo/`
2. One bug = one commit, commit message references issue: `fix: description (fixes #N)`
3. Code quality must survive worldwide public review
4. README.md must be updated after feature progress
5. Version bump must sync Python + DLL
6. Bug tracking: GitHub Issues only, never `.work/bugs.md`
7. Assign yourself before working: `gh issue edit N --add-assignee @me`
8. Label `status:in-progress` when starting, `status:done` when complete
9. All issue comments must include your Agent ID
