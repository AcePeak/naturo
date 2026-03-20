# Naturo 项目状态

> 每个 Agent 启动时**必读**，执行后**必更新自己的状态**

## 🎯 当前目标
**Phase 3 完成 ✅ → 准备推进 Phase 4 (AI Integration)**

## 📍 进度
- [x] Phase 0 — Project Skeleton ✅
- [x] Phase 1 — See ✅
- [x] Phase 1.5 — Snapshot ✅
- [x] Phase 2 — Act ✅
- [x] Phase 2.5 — Deep Capabilities ✅
- [x] **Phase 3 — Stabilize** ✅
  - [x] 错误处理框架 (errors.py)
  - [x] Wait/Retry 策略 (retry.py, wait.py)
  - [x] 进程管理 (process.py)
  - [x] 缓存优化 (cache.py)
  - [x] UI Tree Diff (diff.py)
  - [x] CLI 命令 (wait/app/diff)
  - [x] Stub 命令隐藏
  - [x] Bug 修复 — 37/37 Verified ✅
  - [x] E2E 验收 — QA Round 9 全部通过 ✅
- [ ] **Phase 4 — AI Integration** ← 下一步
- [ ] Phase 5 — Complete

## 🔄 各角色状态

| 角色 | 正在做 | 上次更新 |
|------|--------|----------|
| Dev | **Phase 4 推进** — MCP server 29 tools (编译机验证 ✅)。`mcp` 命令组公开（含 install/start/tools）。Agent 框架实现（agent.py: AIProvider protocol + ToolExecutor + run_agent loop）。714 tests pass (macOS)。下一步: AI provider 实现 (Anthropic/OpenAI) | 3/20 22:30 |
| QA | **Round 10** — Phase 4 MCP Server 首轮验收。BUG-038~040 已全部修复验证。 | 3/20 21:50 |

## 🐛 Bug 概况
- 🔴 Open: 0 个
- 🟢 Fixed: 0 个
- ✅ Verified: 40 个（BUG-007~040 全部验证通过）

详见 `.work/bugs.md`

## 📌 设计原则（不可违反）
1. 未实现的功能不暴露给用户
2. 输出格式和 Peekaboo 一致（PNG 默认）
3. 中文 Windows 兼容
4. 帮助和实际行为始终一致
5. 错误信息面向用户
6. --json 模式下任何输出必须是合法 JSON

�始终一致
5. 错误信息面向用户
6. --json 模式下任何输出必须是合法 JSON

