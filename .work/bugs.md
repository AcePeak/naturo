# Naturo Bug Tracker

状态说明: 🔴 Open | 🟡 Fixing | 🟢 Fixed | ✅ Verified

---

## 🔴 严重

### ✅ BUG-007: `app hide/unhide/switch` stub 暴露给用户
- **状态**: ✅ Verified
- **命令**: `naturo app --help`
- **修复**: hidden=True (commit d181eae)

### ✅ BUG-013: `app launch` 对不存在的应用假报成功
- **状态**: ✅ Verified (Round 4) — 友好错误 "Application not found: nonexistent_app_xyz"，无 traceback，exit code 非零。JSON 模式输出结构化 APP_NOT_FOUND 错误。
- **命令**: `naturo app launch nonexistent_app_xyz`
- **文件**: naturo/process.py

### ✅ BUG-014: `see/find/menu-inspect --json` 错误时输出纯文本
- **状态**: ✅ Verified
- **修复**: commit e6443ea

### ✅ BUG-015: `capture live --app X --json` 错误时输出纯文本
- **状态**: ✅ Verified (part of BUG-014 fix)

### ✅ BUG-016: `wait --json` 超时时输出两段 JSON
- **状态**: ✅ Verified (Round 4) — 只输出一段 JSON，success=false，"success" 仅出现一次，exit code 非零
- **命令**: `naturo wait --element "Button:Save" --timeout 1 --json`
- **修复**: try/except 只包裹 wait 调用本身，JSON 输出逻辑移到 try 外部；用 sys.exit(1) 替代 ctx.exit(1)
- **文件**: naturo/cli/wait_cmd.py

### ✅ BUG-010: Unicode 参数显示乱码
- **状态**: ✅ Verified
- **修复**: commit 77f3b1d

## 🟡 中等

### ✅ BUG-008: `app find` 找不到时退出码为 0
- **状态**: ✅ Verified
- **修复**: commit a97771a

### ✅ BUG-011: `find --json` 无窗口时输出纯文本
- **状态**: ✅ Verified (merged into BUG-014)

### BUG-017: 中文路径导致临时文件失败 + 残留
- **状态**: ✅ Verified (Round 3) — 中文路径创建成功，合法 PNG (magic bytes 89504e47)，无临时文件残留
- **命令**: `naturo capture live --path test_中文.png`
- **修复**: 使用 tempfile.mkstemp + 失败时清理
- **文件**: naturo/backends/windows.py

### ✅ BUG-018: `app relaunch` 对不存在的应用也假报成功
- **状态**: ✅ Verified (Round 4) — 友好错误 "Application not found: nonexistent_xyz"，无 traceback，exit code 非零
- **命令**: `naturo app relaunch nonexistent_xyz`
- **文件**: naturo/process.py

### ✅ BUG-019: `press --count 0` 和 `--count -1` 不报错
- **状态**: ✅ Verified
- **修复**: commit ae0ebcb

## 🟢 低

### ✅ BUG-009: `app find ""` 匹配到 System Idle Process
- **状态**: ✅ Verified
- **修复**: commit fe31b2c

### ✅ BUG-012: `list windows` 无桌面时返回空数组无提示
- **状态**: ✅ Verified
- **修复**: commit 259bf92

### ✅ BUG-020: `wait --timeout -1` 不校验
- **状态**: ✅ Verified
- **修复**: commit ce840ae

### ✅ BUG-021: `snapshot clean --days -1` 不校验
- **状态**: ✅ Verified
- **修复**: commit ce840ae

---

## 🆕 Round Full 新发现

### BUG-022: `snapshot clean` 无参数时 exit code 为 0
- **状态**: ✅ Verified (Round 5) — stderr 输出 "Error: Specify --days N or --all."，exit code 1。JSON 模式输出 INVALID_INPUT 结构化错误。
- **命令**: `naturo snapshot clean`
- **修复**: err=True + SystemExit(1)
- **文件**: naturo/cli/snapshot.py

### BUG-023: `learn` 不存在的 topic 静默 fallback
- **状态**: ✅ Verified (Round 5) — 报错 "Error: Unknown topic: nonexistent_topic"，列出可用 topics，exit code 1。
- **命令**: `naturo learn nonexistent_topic`
- **文件**: naturo/cli/core.py

### BUG-024: JSON 输出格式不一致（`ok` vs `success`）
- **状态**: ✅ Verified (Round 5) — click/type/press/scroll 全部统一为 `{"success": bool, "error": {"code": "...", "message": "..."}}` 格式，exit code 与 success 字段一致。
- **严重度**: 中（影响 AI agent 集成）
- **文件**: naturo/cli/interaction.py

### BUG-025: `scroll -a 0` 和 `-a -1` 无边界校验
- **状态**: ✅ Verified (Round 5) — `scroll -a 0` 和 `-a -1` 均报 "Error: --amount must be >= 1, got X"，exit code 1。
- **命令**: `naturo scroll -a 0`, `naturo scroll -a -1`
- **文件**: naturo/cli/interaction.py

### BUG-026: `menu-inspect --app nonexistent` 不区分应用不存在
- **状态**: ✅ Verified (Round 5) — 输出 "Error: Application not found: nonexistent"，JSON 模式返回 APP_NOT_FOUND 错误码，exit code 1。
- **命令**: `naturo menu-inspect --app nonexistent`
- **文件**: naturo/cli/core.py

### BUG-027: `menu-inspect` success=false 时 exit code 为 0
- **状态**: ✅ Verified (Round 5) — success=false 时 exit code 为 1。
- **命令**: `naturo menu-inspect --json`
- **文件**: naturo/cli/core.py

### BUG-028: `see/find --depth` 边界值无校验
- **状态**: ✅ Verified (Round 5) — depth 0/-1/11 均报 "Error: --depth must be between 1 and 10, got X"，exit code 1。
- **命令**: `naturo see --depth 0`, `naturo see --depth -1`, `naturo find Save --depth 0`
- **文件**: naturo/cli/core.py

---

## 🆕 Round 6 自发现（E2E 验收前扫描）

### BUG-029: `list windows --json` 和 `snapshot list --json` 返回裸数组
- **状态**: ✅ Verified (Round 9) — `list windows --json` 返回 `{"success": true, "windows": [...]}`，`snapshot list --json` 返回 `{"success": true, "snapshots": [...]}`，格式统一。
- **严重度**: 中（影响 AI agent 集成 — JSON schema 不一致）
- **现象**: 其他命令的 `--json` 成功响应都是 `{"success": true, ...}` 对象，但 `list windows --json` 和 `snapshot list --json` 直接返回裸数组 `[...]`
- **命令**: `naturo list windows --json`, `naturo snapshot list --json`
- **预期**: `{"success": true, "windows": [...]}` 和 `{"success": true, "snapshots": [...]}`
- **文件**: naturo/cli/core.py (windows 函数), naturo/cli/snapshot.py (snapshot_list 函数)

### BUG-030: `capture live --json` 成功时缺少 `success` 字段
- **状态**: ✅ Verified (Round 7) — 成功时输出 `{"success": true, "path":..., "width":..., "height":..., "format":..., "snapshot_id":...}`。
- **严重度**: 中（JSON schema 不一致）
- **现象**: 成功时输出 `{"path":..., "width":..., "height":..., "format":..., "snapshot_id":...}`，缺少 `"success": true`
- **对比**: `app list --json` 和 `app find --json` 都有 `success` 字段
- **命令**: `naturo capture live --json`
- **文件**: naturo/cli/core.py (capture live 相关)

### BUG-031: `snapshot clean --json` 成功时缺少 `success` 字段
- **状态**: ✅ Verified (Round 9) — `snapshot clean --days 9999 --json --yes` 返回 `{"success": true, "deleted": 0}`，格式正确。
- **严重度**: 低（JSON schema 不一致）
- **现象**: 成功删除时输出 `{"deleted": N}`，缺少 `"success": true`
- **命令**: `naturo snapshot clean --days 30 --json`
- **文件**: naturo/cli/snapshot.py (snapshot_clean 函数 line 117-118)

### BUG-032: `type --wpm` 无边界校验
- **状态**: ✅ Verified (Round 9) — `--wpm 0` 报 "Error: --wpm must be >= 1, got 0"，`--wpm -1` 报错，均 exit code 非零。
- **严重度**: 低（同 BUG-019/BUG-025 类型）
- **现象**: `--wpm 0` 和 `--wpm -1` 不报错，直接传给后端
- **命令**: `naturo type --wpm 0 hello`, `naturo type --wpm -1 hello`
- **预期**: 校验 wpm >= 1，否则报 "Error: --wpm must be >= 1, got X"
- **文件**: naturo/cli/interaction.py

---

---

## 🆕 Round 7 自发现

### BUG-033: `drag --steps 0`/`--steps -1` 和 `--duration -1` 无边界校验
- **状态**: ✅ Verified (Round 8) — `--steps 0` 报 "Error: --steps must be >= 1, got 0"，`--steps -1` 报错，`--duration -1` 报 "Error: --duration must be >= 0, got -1.0"，全部 exit code 1。
- **严重度**: 低（同 BUG-019/025/032 类型）
- **现象**: `--steps 0`、`--steps -1`、`--duration -1` 均不报错，直接传给后端
- **命令**: `naturo drag --from-coords 100 100 --to-coords 200 200 --steps 0`, `--steps -1`, `--duration -1`
- **预期**: `--steps >= 1`，`--duration >= 0`，否则报 "Error: --steps must be >= 1, got X"
- **文件**: naturo/cli/interaction.py (drag 函数)

### BUG-034: `wait --interval -1` 泄漏 Python 内部错误
- **状态**: ✅ Verified (Round 9) — `--interval -1` 返回 `{"success": false, "error": {"code": "INVALID_INPUT", "message": "--interval must be > 0, got -1.0"}}`，`--interval 0` 同理，均 exit code 1。
- **严重度**: 中（错误信息面向用户原则违反 + 同类遗漏）
- **现象**: `naturo wait --interval -1 --element test --json` 返回 `{"success": false, "error": {"code": "UNKNOWN_ERROR", "message": "sleep length must be non-negative"}}`，泄漏 Python sleep 内部错误
- **命令**: `naturo wait --interval -1 --element test --json`
- **预期**: 校验 `--interval > 0`，报 "Error: --interval must be > 0, got -1.0"。同时 `--interval 0` 应该被拒绝（导致 CPU 空转）
- **文件**: naturo/cli/wait_cmd.py

---

---

## 🆕 Round 8 自发现

### BUG-035: `click --wait-for` 参数声明了但未实现
- **状态**: ✅ Verified (Round 9) — `click --help` 不再显示 `--wait-for` 参数，已隐藏。
- **严重度**: 中（帮助和行为不一致 — 设计原则 #4 违反）
- **现象**: `click --help` 显示 `--wait-for FLOAT  Wait for element (seconds)`，但函数体中 `wait_for` 参数被接收后从未使用，传任何值都无效
- **命令**: `naturo click --wait-for 5 --coords 100 100`（不会等待 5 秒）
- **修复**: hidden=True 隐藏参数，保留向后兼容（commit 9dcf5de）
- **文件**: naturo/cli/interaction.py (click 函数)

### BUG-036: `move --duration` 参数声明了但未传给 backend
- **状态**: ✅ Verified (Round 9) — `move --help` 不再显示 `--duration` 参数，已隐藏。
- **严重度**: 低（帮助和行为不一致 — 设计原则 #4 违反）
- **现象**: `move --help` 显示 `--duration FLOAT  Move duration (seconds)`，但 `move()` 函数中调用 `backend.move_mouse(x, y)` 时没传 duration 参数，且无边界校验
- **命令**: `naturo move --duration 2 --coords 100 100`（不会花 2 秒移动）
- **修复**: hidden=True 隐藏参数，保留向后兼容（commit 9cb6539）
- **文件**: naturo/cli/interaction.py (move 函数)

### BUG-037: `hotkey --hold-duration` 无边界校验
- **状态**: ✅ Verified (Round 9) — `--hold-duration -1` 报 "Error: --hold-duration must be >= 0, got -1.0"，exit code 非零。`--hold-duration 0` 正常接受。
- **严重度**: 低（同 BUG-019/025/032/033 类型）
- **现象**: `--hold-duration -1` 和 `--hold-duration 0` 不校验，负值直接传给 backend（`hold_duration_ms=int(hold_duration)`）
- **命令**: `naturo hotkey --hold-duration -1 ctrl+c`
- **修复**: 校验 hold_duration >= 0，负值报 INVALID_INPUT 错误（commit c35a0f7）
- **文件**: naturo/cli/interaction.py (hotkey 函数)

*Dev Agent 修复后更新状态为 🟢 Fixed，QA 验证后更新为 ✅ Verified*

---

## 🆕 Phase 4 (MCP Server) — Round 10 续

### BUG-038: `hotkey` MCP tool 使用 `*keys` 导致完全无法调用
- **状态**: ✅ Verified — 已改为 `keys: list[str]`，空列表返回 INVALID_INPUT 错误
- **严重度**: 🔴 严重（AI Agent 核心功能完全不可用）
- **现象**: `hotkey` 工具定义为 `def hotkey(*keys: str)`，使用 Python varargs。FastMCP 将其转换为 JSON schema `{"keys": {"type": "string"}}`（单个 string），MCP 客户端传 `keys="ctrl+s"` 时报 `got an unexpected keyword argument 'keys'`
- **影响**: 所有 AI agent 尝试按快捷键时都会失败。这是 MCP 26 个工具中唯一一个完全无法工作的
- **修复**: 改为 `def hotkey(keys: list[str])`，空列表返回 INVALID_INPUT
- **文件**: naturo/mcp_server.py (hotkey 函数)

### BUG-039: MCP tool 缺少统一异常处理，backend 异常泄漏 Python 内部错误
- **状态**: ✅ Verified — 已添加 `@_safe_tool` 装饰器包装所有 26 个工具
- **严重度**: 🟡 中等（影响 AI agent 体验和错误恢复）
- **现象**: MCP 工具没有 try/except 包装 backend 调用。当 backend 抛出异常（如 COM error、NaturoCoreError）时，异常直接冒泡给 MCP 框架，AI agent 收到的是 Python traceback 而非结构化错误
- **修复**: `_safe_tool` 装饰器捕获所有异常，返回 `{"success": false, "error": {"code": "...", "message": "..."}}`
- **文件**: naturo/mcp_server.py（所有 tool 函数）

### BUG-040: `test_process.py::TestLaunchApp` 5 个测试因 mock 问题全挂
- **状态**: ✅ Verified — 已 mock `subprocess.run` alongside `subprocess.Popen`，Windows Python 3.14 全过
- **严重度**: 🟡 中等（测试基础设施问题，不影响产品功能）
- **现象**: `@patch("subprocess.Popen")` 同时影响了 `subprocess.run()`（run 内部用 Popen），导致 `where` 命令的 mock 结果格式错误：`ValueError: not enough values to unpack (expected 2, got 0)`
- **修复**: mock `naturo.process.subprocess.run` 和 `naturo.process.subprocess.Popen`（commit 8c8fb7a）
- **文件**: tests/test_process.py (TestLaunchApp 类)

---

## 🆕 Round 11 自发现（MCP Server 深度测试）

### BUG-041: `mcp start --port/--host` 参数被忽略，始终绑定 127.0.0.1:8000
- **状态**: 🟢 Fixed
- **严重度**: 🔴 严重（MCP server 端口不可配置，多实例/代理场景完全不可用）
- **现象**: `naturo mcp start --transport sse --port 3100` 实际绑定到 `127.0.0.1:8000`。`--port 9999 --host 0.0.0.0` 同样无效。help 文档声称默认端口 3100，实际是 uvicorn 默认 8000
- **根因**: `run_server()` 接收了 host/port 参数但 `server.run(transport=transport)` 没传递
- **命令**: `naturo mcp start --transport sse --port 3100`
- **预期**: 绑定到 `localhost:3100`
- **实际**: 绑定到 `127.0.0.1:8000`
- **文件**: naturo/mcp_server.py (run_server 函数，第 881 行)

### BUG-042: `mcp install --json` 在 JSON 前混入纯文本 "Installing MCP dependencies..."
- **状态**: 🟢 Fixed
- **严重度**: 🟡 中等（违反设计原则 #6 — --json 模式下任何输出必须是合法 JSON）
- **现象**: stdout 输出 `Installing MCP dependencies...\n{"success": true, ...}`，前缀文本导致 JSON 解析失败
- **命令**: `naturo mcp install --json`
- **预期**: stdout 只输出 JSON，进度信息走 stderr 或不输出
- **文件**: naturo/cli/ai.py (install 函数，约第 110 行 `click.echo("Installing MCP dependencies...")`)

### BUG-043: `mcp start` 失败时 `--json` 不输出 JSON（uvicorn 日志泄漏）
- **状态**: 🟢 Fixed
- **严重度**: 🟡 中等（违反设计原则 #6 + 错误信息不友好）
- **现象**: `naturo mcp start --transport sse --json` 端口被占用时，输出 uvicorn 的 INFO/ERROR 日志文本而非 JSON。异常被 uvicorn 内部处理，没到 CLI 的 except 分支
- **命令**: `naturo mcp start --transport sse --json`（端口被占用时）
- **预期**: `{"success": false, "error": {"code": "SERVER_ERROR", "message": "Port 8000 already in use"}}`
- **实际**: `INFO: Started server process...` + `ERROR: [Errno 10048]...`
- **文件**: naturo/cli/ai.py (start 函数) + naturo/mcp_server.py (run_server)
