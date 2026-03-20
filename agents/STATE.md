# Naturo 项目状态

> 每个 Agent 启动时**必读**，执行后**必更新自己的状态**

## 🎯 当前目标
**Phase 3 (Stabilize) — Bug 全清零，E2E 验收通过**

## 📍 进度
- [x] Phase 0 — Project Skeleton ✅
- [x] Phase 1 — See ✅
- [x] Phase 1.5 — Snapshot ✅
- [x] Phase 2 — Act ✅
- [x] Phase 2.5 — Deep Capabilities ✅
- [ ] **Phase 3 — Stabilize** ← 当前
  - [x] 错误处理框架 (errors.py)
  - [x] Wait/Retry 策略 (retry.py, wait.py)
  - [x] 进程管理 (process.py)
  - [x] 缓存优化 (cache.py)
  - [x] UI Tree Diff (diff.py)
  - [x] CLI 命令 (wait/app/diff)
  - [x] Stub 命令隐藏
  - [ ] **Bug 修复** ← 进行中
  - [ ] E2E 验收通过
- [ ] Phase 4 — AI Integration
- [ ] Phase 5 — Complete

## 🔄 各角色状态

| 角色 | 正在做 | 上次更新 |
|------|--------|----------|
| Dev | **待命** — BUG-035~037 修复完毕 (总 37 个)，639 tests pass，等待 QA 验证后 Phase 3 结项 → Phase 4 | 3/20 20:11 |
| QA | **Round 7** — BUG-029~032 全部验证通过 ✅ + 自发现 2 个新 bug (BUG-033~034: drag/wait 边界校验遗漏) | 3/20 19:45 |

## 🐛 Bug 概况
- 🔴 Open: 0 个
- 🟢 Fixed: 3 个 (BUG-035~037，等待 QA 验证)
- ✅ Verified: 34 个（BUG-007~034 全部验证通过）

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

