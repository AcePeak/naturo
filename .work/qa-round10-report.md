# QA Round 10 — Phase 4 MCP Server 首轮验收

**日期**: 2026-03-20
**测试环境**: 编译机 192.168.31.52 (Windows, Python 3.12.10) + 本地 macOS 代码审查
**分支**: feat/phase3-stabilize (commit 900903f)

## 测试范围

### 1. MCP Server 基础验证
- ✅ `naturo mcp tools` 正常列出 26 个工具
- ✅ `naturo mcp tools --json` 输出合法 JSON，包含所有工具描述
- ✅ `naturo mcp start --help` 正常，支持 stdio/sse/streamable-http
- ✅ Server 创建成功 (`create_server()` 返回 FastMCP 实例)
- ✅ pip install -e ".[mcp]" 正常安装 MCP 依赖

### 2. MCP 单元测试
- ✅ 46/46 测试全部通过 (1.89s)
- 覆盖：server 创建、工具注册、所有输入验证、响应格式一致性

### 3. 全量测试套件
- 722 passed / 90 failed / 94 skipped (23.36s)
- 85 个失败为 SSH 无桌面 session 的已知限制（mouse/keyboard/window 需要交互式桌面）
- 5 个失败为 test_process.py mock 问题 (BUG-040)

### 4. MCP 代码审查（人肉 + 静态分析）
- 审查了所有 26 个 tool 的参数定义、返回格式、边界校验
- AST 分析发现 `hotkey` 使用 *args 的致命问题 (BUG-038)

## 发现的 Bug

| Bug ID | 严重度 | 描述 |
|--------|--------|------|
| BUG-038 | 🔴 严重 | `hotkey` MCP tool 使用 `*keys` varargs，MCP 完全无法调用 |
| BUG-039 | 🟡 中等 | MCP tools 缺少 try/except，backend 异常泄漏 Python 内部错误 |
| BUG-040 | 🟡 中等 | test_process.py 5 个测试 mock 错误，launch_app 缺少测试覆盖 |

## E2E 验收
- ⚠️ 无法在编译机通过 SSH 执行完整 E2E（需要交互式桌面 session）
- 截屏功能正常：`naturo capture live` 成功输出 1024x768 PNG
- `naturo app launch notepad` 成功启动 PID 3644
- 但 `list windows` 在 SSH session 中返回空（已知限制）
- **建议**: 需要 RDP 或 VNC 连接到编译机执行 E2E，或在编译机上部署一个 agent 在桌面 session 中执行

## 产品质量评估

**Phase 3 质量**: ⭐⭐⭐⭐⭐ — 37/37 bug 全部验证通过，CLI 层面非常扎实

**Phase 4 MCP 质量**: ⭐⭐⭐☆☆ — 整体架构清晰，但有 1 个致命 bug 和 1 个中等问题需要修复

### Top 3 改进建议
1. **BUG-038 必须立即修**: hotkey 是 AI agent 最常用的工具之一，完全不可用是 blocker
2. **统一异常处理**: 给所有 MCP tool 加 try/except wrapper，保证 AI agent 永远收到结构化错误
3. **E2E 自动化**: 在编译机桌面 session 部署一个常驻测试 runner，支持远程触发 E2E

### 风险预警
- `hotkey` 以外的 25 个工具只有 mock 测试，缺少真机 MCP 协议级别的 E2E 测试
- 编译机 SSH 无法做 GUI 自动化测试，当前测试覆盖有盲区
- test_process.py 的 mock 问题掩盖了 launch_app 在 Windows 上的真实行为
