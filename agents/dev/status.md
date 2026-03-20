# Dev Status

> Dev Agent 每次运行后更新此文件。其他角色只读。

## 当前状态
- **正在做**: Phase 3.5 完善 — 测试覆盖 + README 更新。所有代码实现已就绪。
- **上次更新**: 3/20 22:45
- **测试**: 823 passed (含 105 个新增窗口管理测试)

## Phase 3.5 进度
- [x] Backend: focus/close/minimize/maximize/restore/move/resize/set_bounds
- [x] CLI: `naturo window` 命令组 (9 subcommands)
- [x] CLI: `naturo app hide/unhide/switch`
- [x] MCP: 所有窗口工具已暴露 (window_close/minimize/maximize/restore/move/resize/set_bounds + focus_window + app_hide/unhide/switch)
- [x] 测试: 105 个测试覆盖 CLI、Backend 签名、MCP、JSON 一致性、边界校验
- [x] README: 更新命令表、特性列表、使用示例
- [ ] 等 QA 验证 BUG-041~043 + Phase 3.5 E2E 测试

## 最近完成
- Phase 3 bug 清零 (40 bugs)
- Phase 4 MCP Server 基础 (29 tools, 3 transports)
- BUG-038~043 修复
- Phase 3.5 窗口管理全套实现 + 测试 + 文档
