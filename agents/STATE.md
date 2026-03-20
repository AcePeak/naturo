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
| Dev | **Phase 4 启动** — MCP server 基础实现完成 (20+ tools, stdio/sse/streamable-http transport)。CLI: `naturo mcp start/tools`。639 tests pass。下一步: MCP 编译机实测 + agent 命令实现 | 3/20 21:11 |
| QA | **Round 9** — BUG-029,031,032,034~037 全部验证通过 ✅。0 Open / 0 Fixed / 37 Verified。Phase 3 Bug 全清零 🎉 | 3/20 20:40 |

## 🐛 Bug 概况
- 🔴 Open: 0 个
- 🟢 Fixed: 0 个
- ✅ Verified: 37 个（BUG-007~037 全部验证通过）

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

