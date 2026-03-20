# Naturo 项目状态

> 每个 Agent 启动时**必读**。
> **更新规则**：只更新自己角色对应的状态文件，不要编辑此文件。

## 🎯 当前目标
**Phase 3.5 (Window Management) — 补齐窗口操作，对齐 Peekaboo**

## 📍 进度
- [x] Phase 0 — Project Skeleton ✅
- [x] Phase 1 — See ✅
- [x] Phase 1.5 — Snapshot ✅
- [x] Phase 2 — Act ✅
- [x] Phase 2.5 — Deep Capabilities ✅
- [x] Phase 3 — Stabilize ✅ (43 bugs fixed, 700+ tests)
- [ ] **Phase 3.5 — Window Management** ← 当前
- [ ] Phase 4 — AI Integration (MCP server 基础已完成, 29 tools)
- [ ] Phase 4.5 — Dialog & System Integration
- [ ] Phase 5 — Complete (自然机器人引擎差异化)
- [ ] Phase 5.1 — Open Source Launch

## 🔄 各角色状态
- **Dev**: 见 `agents/dev/status.md`
- **QA**: 见 `agents/qa/status.md`

## 📌 设计原则（不可违反）
1. 未实现的功能不暴露给用户
2. 输出格式和 Peekaboo 一致（PNG 默认）
3. 中文 Windows 兼容
4. 帮助和实际行为始终一致
5. 错误信息面向用户
6. --json 模式下任何输出必须是合法 JSON
7. 一个 bug = 一个 commit
8. 只操作 ~/Ace/naturo/，禁止其他项目
9. 代码质量要经得起全世界 review（仓库已 public）
10. README.md 每次功能进展后同步更新
