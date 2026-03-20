# Naturo 项目状态

> 每个 Agent 启动时**必读**，执行后**必更新自己的状态**

## 🎯 当前目标
**Phase 3.5 (Window Management) — 补齐窗口操作，对齐 Peekaboo**

## 📍 进度
- [x] Phase 0 — Project Skeleton ✅
- [x] Phase 1 — See ✅
- [x] Phase 1.5 — Snapshot ✅
- [x] Phase 2 — Act ✅
- [x] Phase 2.5 — Deep Capabilities ✅
- [x] Phase 3 — Stabilize ✅ (40 bugs fixed, 700+ tests)
- [ ] **Phase 3.5 — Window Management** ← 当前
- [ ] Phase 4 — AI Integration (MCP server 基础已完成)
- [ ] Phase 4.5 — Dialog & System Integration
- [ ] Phase 5 — Complete (自然机器人引擎差异化)
- [ ] Phase 5.1 — Open Source Launch

## 🔄 各角色状态

| 角色 | 正在做 | 上次更新 |
|------|--------|----------|
| Dev | 修复 BUG-041~043 (MCP port/host、JSON 输出)，待 QA 验证 | 3/20 22:20 |
| QA | **Round 11** — MCP Server 深度测试。发现 BUG-041~043（端口参数无效、JSON 输出混杂、错误日志泄漏） | 3/20 22:20 |

## 🐛 Bug 概况
- 🔴 Open: 0
- 🟢 Fixed 待验证: 3 (BUG-041~043)
- ✅ Verified: 40

## 📋 当前优先级
1. **Phase 3.5** — 窗口管理 (focus/close/minimize/maximize/move/resize/set-bounds)
   - C++ DLL 层：Win32 API (ShowWindow, MoveWindow, SetWindowPos, SetForegroundWindow)
   - Python bridge 层：新增 bridge 函数
   - CLI 层：`naturo window` 命令组
   - MCP 层：暴露为 MCP tools
2. **Phase 4 继续** — AI vision + agent 命令 + 录制回放
3. **Phase 4.5** — Dialog 处理 + 系统集成

## 📌 设计原则（不可违反）
1. 未实现的功能不暴露给用户
2. 输出格式和 Peekaboo 一致（PNG 默认）
3. 中文 Windows 兼容
4. 帮助和实际行为始终一致
5. 错误信息面向用户
6. --json 模式下任何输出必须是合法 JSON
7. 一个 bug = 一个 commit
8. 只操作 ~/Ace/naturo/，禁止其他项目
