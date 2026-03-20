# Naturo 项目状态

> 每个 Agent 启动时**必读**。
> **更新规则**：只更新自己角色对应的状态文件，不要编辑此文件。

## 🎯 当前目标
**全速推进，尽快达到并超越 Peekaboo。Ace 休息中，大胆往前做。**

当前优先级：
1. Phase 3.5 QA 验证 + CI 修绿
2. Phase 4 AI Integration 继续（vision + agent command + recording）
3. Phase 4.5 Dialog & System Integration
4. Phase 5A Multi-Monitor + DPI

## 📍 进度
- [x] Phase 0 — Project Skeleton ✅
- [x] Phase 1 — See ✅
- [x] Phase 1.5 — Snapshot ✅
- [x] Phase 2 — Act ✅
- [x] Phase 2.5 — Deep Capabilities ✅
- [x] Phase 3 — Stabilize ✅ (43 bugs fixed, 700+ tests)
- [x] Phase 3.5 — Window Management ✅ (代码完成，QA 验证中)
- [ ] **Phase 4 — AI Integration** ← 继续推进
- [ ] Phase 4.5 — Dialog & System Integration
- [ ] Phase 5A — Multi-Monitor + DPI
- [ ] Phase 5B — 自然机器人引擎移植
- [ ] Phase 5.1 — Open Source Launch

## 🔄 各角色状态
- **Dev**: 见 `agents/dev/status.md`
- **QA**: 见 `agents/qa/status.md`

## ⚠️ 紧急
- CI Ubuntu 测试失败：test_process.py::TestLaunchApp::test_launch_nonexistent_app_returns_error（跨平台兼容）
- Dev 优先修 CI，然后继续 Phase 4

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
