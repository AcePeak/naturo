# QA Report — Round 1 自发现测试

## 环境信息
- **naturo**: 0.1.0
- **Python**: 3.14.3
- **系统**: Windows 11 专业版 (10.0.22621)
- **测试方式**: SSH (llfac@100.94.85.44)，无桌面 session
- **测试时间**: 2026-03-20 17:07-17:20 GMT+8

## 命令发现

```
naturo (v0.1.0)
├── app
│   ├── find      [NAME, --pid, --json]
│   ├── launch    [NAME, --path, --wait-until-ready, --timeout, --no-focus, --args, --json]
│   ├── quit      [--name, --pid, --force, --timeout, --json]
│   ├── list      [--json]
│   ├── switch    [NAME, --json]           ← Not implemented
│   ├── hide      [NAME, --pid, --json]    ← Not implemented
│   ├── unhide    [NAME, --pid, --json]    ← Not implemented
│   └── relaunch  [NAME, --wait-until-ready, --timeout, --json]
├── capture
│   └── live      [--app, --window-title, --hwnd, --screen, --path, --format, --snapshot/--no-snapshot, --json]
├── click         [QUERY, --on, --id, --coords, --double, --right, --app, --pid, --window-title, --hwnd, --wait-for, --input-mode, --process-name, --json]
├── diff          [--snapshot (×2), --window, --interval, --json]
├── drag          [--from, --from-coords, --to, --to-coords, --duration, --steps, --modifiers, --profile, --app, --window-title, --hwnd, --json]
├── find          [QUERY, --role, --actionable, --depth, --limit, --json]
├── hotkey        [KEYS, --keys, --hold-duration, --app, --window-title, --hwnd, --input-mode, --json]
├── learn         [TOPIC]
├── list
│   └── windows   [--app, --process-name, --pid, --json]
├── menu-inspect  [--app, --flat, --json]
├── move          [--to, --coords, --id, --duration, --app, --window-title, --hwnd, --json]
├── paste         [TEXT, --file, --restore, --app, --window-title, --hwnd, --json]
├── press         [KEY, --count, --delay, --app, --window-title, --hwnd, --input-mode, --json]
├── scroll        [--direction, --amount, --on, --smooth, --delay, --app, --window-title, --hwnd, --json]
├── see           [--app, --window-title, --hwnd, --pid, --mode, --depth, --path, --annotate, --snapshot/--no-snapshot, --json]
├── snapshot
│   ├── list      [--json]
│   └── clean     [--days, --all, --yes, --json]
├── type          [TEXT, --delay, --profile, --wpm, --return, --tab, --escape, --delete, --clear, --app, --window-title, --hwnd, --input-mode, --process-name, --json]
└── wait          [--element, --window, --gone, --timeout, --interval, --json]
```

---

## 测试结果

### ❌ 失败 (12)

#### BUG-R1-001: `app launch` 对不存在的应用返回 success
- **命令**: `naturo app launch nonexistent_app_xyz`
- **期望**: 报错 "Application not found" 或类似，exit code != 0
- **实际**: `Launched nonexistent_app_xyz (PID: 31584)` exit code 0
- **JSON 也是**: `{"success": true, "process": {"pid": 21004, "name": "nonexistent_app_xyz", ...}}`
- **验证**: `tasklist /FI "PID eq 31584"` 无匹配进程，`app find nonexistent_app_xyz` 返回 Not found
- **严重性**: 🔴 严重 — 误导用户和 AI agent 认为应用已启动
- **举一反三**: `app relaunch` 也有同样问题

#### BUG-R1-002: `app relaunch` 对不存在的应用也返回 success
- **命令**: `naturo app relaunch nonexistent_xyz`
- **期望**: 报错
- **实际**: `Relaunched nonexistent_xyz (PID: 31056)` exit code 0
- **严重性**: 🔴 严重

#### BUG-R1-003: `app switch/hide/unhide` 输出 "Not implemented yet" 但 exit code = 0
- **命令**: `naturo app switch chrome`, `naturo app hide chrome`, `naturo app unhide chrome`
- **期望**: 要么功能可用，要么不暴露在 --help 中（参见 BUG-004 历史）
- **实际**: 输出 `Not implemented yet — coming in Phase 2`，exit code 0
- **JSON 模式**: 同样输出纯文本 "Not implemented yet"，不是 JSON！
- **严重性**: 🔴 严重 — 直接违反设计原则 #1 "未实现的功能不暴露给用户"，且 exit code=0 误导自动化
- **举一反三**: 所有子命令都需检查是否 stub

#### BUG-R1-004: `see --json` 无窗口时输出纯文本而非 JSON
- **命令**: `naturo see --json`（SSH 无桌面 session）
- **期望**: JSON 格式错误输出如 `{"success": false, "error": {...}}`
- **实际**: 纯文本 `No window found or UI tree is empty.`
- **JSON 解析**: `json.loads()` 抛出 `JSONDecodeError`
- **严重性**: 🔴 严重 — `--json` 模式下必须始终输出合法 JSON

#### BUG-R1-005: `find --json` 无窗口时输出纯文本而非 JSON
- **命令**: `naturo find "Save" --json`
- **期望**: JSON 格式
- **实际**: 纯文本 `No window found or UI tree is empty.`
- **严重性**: 🔴 严重 — 同 BUG-R1-004

#### BUG-R1-006: `menu-inspect --json` 无菜单时输出纯文本而非 JSON
- **命令**: `naturo menu-inspect --json`
- **期望**: JSON 格式
- **实际**: 纯文本 `No menu items found.`
- **严重性**: 🔴 严重 — 同 BUG-R1-004

#### BUG-R1-007: `capture live --app X --json` 错误时输出纯文本而非 JSON
- **命令**: `naturo capture live --app nonexistent --json`
- **期望**: `{"success": false, "error": {...}}`
- **实际**: 纯文本 `Error: Window not found: nonexistent`（不是 JSON）
- **严重性**: 🟡 中等

#### BUG-R1-008: `capture live` 中文路径导致临时文件失败 + 残留
- **命令**: `naturo capture live --path test_中文.png`
- **期望**: 成功保存文件
- **实际**: `Error: [Errno 2] No such file or directory: 'test_中文.png.tmp.bmp'`（注意乱码）
- **残留**: `test_中文.png.tmp.bmp` 和 `test 空格.png.tmp.bmp` 文件残留在目录中（后者名称也是乱码后的结果）
- **严重性**: 🟡 中等 — 中文 Windows 必须支持中文路径（设计原则 #3）
- **注**: 英文空格路径 `test with space.png` 能正常工作

#### BUG-R1-009: `press --count 0` 和 `--count -1` 不报错
- **命令**: `naturo press enter --count 0` / `naturo press enter --count -1`
- **期望**: 报错或忽略无效值
- **实际**: 输出 `action: pressed / key: enter / count: 0`（或 -1），exit code 0
- **严重性**: 🟡 中等 — 边界值应校验

#### BUG-R1-010: `wait --json` 超时时 success=true + found=false
- **命令**: `naturo wait --element "Button:Save" --timeout 1 --json`
- **期望**: `{"success": false, ...}` 并且 exit code != 0
- **实际**: `{"success": true, "found": false, ...}` exit code 0
- **非 JSON 模式**: 正确输出 `Timeout after 1.0s` + exit code 1
- **严重性**: 🔴 严重 — JSON 和非 JSON 模式行为不一致。success=true 但 found=false 误导 AI agent

#### BUG-R1-011: `wait --timeout -1` 不报错
- **命令**: `naturo wait --timeout -1 --element "Button:Save"`
- **期望**: 报错或立即返回 timeout
- **实际**: 输出 `Timeout after 0.0s` exit code 1（表现正常但应该在参数层面拒绝）
- **严重性**: 🟢 低

#### BUG-R1-012: `snapshot clean --days -1 --yes` 不报错
- **命令**: `naturo snapshot clean --days -1 --yes`
- **期望**: 报错或忽略
- **实际**: `Deleted 0 snapshot(s).` exit code 0
- **严重性**: 🟢 低 — 负数天数无意义但不会造成破坏

---

### ✅ 通过 (28)

- `naturo --version` — 输出 `naturo, version 0.1.0`，exit code 0
- `naturo --help` — 显示所有命令，无 stub 命令泄露（主层级）
- `naturo app list` — 列出 102 个进程，格式正确
- `naturo app list --json` — 合法 JSON，有 success/apps/count 字段
- `naturo app find chrome` — 正确找到 chrome.exe
- `naturo app find chrome --json` — 合法 JSON，字段完整
- `naturo app find nonexistent_app_xyz` — 正确返回 "Not found"
- `naturo app find nonexistent_app_xyz --json` — 合法 JSON，process=null
- `naturo app find Feishu` — 正确找到 Feishu.exe（大小写模糊匹配）
- `naturo app find Weixin` — 正确找到 Weixin.exe
- `naturo app find ""` — 模糊匹配返回第一个结果（可讨论）
- `naturo app find`（无参数）— 正确报错 Missing argument
- `naturo app launch notepad` — 成功启动，PID 正确
- `naturo app launch notepad --json` — 合法 JSON
- `naturo app launch ""` — 正确报错 "no name or path provided"
- `naturo app quit --name notepad` — 正确终止（已运行的 notepad 先退出了）
- `naturo app quit --name nonexistent --json` — 合法 JSON，error 结构含 code/message/category
- `naturo app quit`（无参数）— 正确报错 "Specify --name or --pid"
- `naturo list windows` — 输出 "No windows found"（SSH 无桌面，正常）
- `naturo list windows --json` — 合法 JSON `[]`
- `naturo capture live` — 成功保存 capture.png，文件 magic bytes = `89 50 4e 47`（PNG ✅）
- `naturo capture live --json` — 合法 JSON，含 path/width/height/format/snapshot_id
- `naturo capture live --format jpg` — 成功保存，magic bytes = `ff d8 ff`（JPEG ✅）
- `naturo capture live --format bmp` — 成功保存，magic bytes = `42 4d`（BMP ✅）
- `naturo capture live --path "test with space.png"` — 空格路径正常工作
- `naturo capture live --no-snapshot --json` — 合法 JSON，无 snapshot_id 字段
- `naturo snapshot list` / `--json` — 正常
- `naturo snapshot clean --all --yes` — 正常清理

---

### ⏭️ 跳过 (8) [SKIP-NO-DESKTOP]

以下命令因 SSH 无桌面 session 返回 `System/COM error`，属于预期行为：

- `naturo click --coords 100 100` — System/COM error
- `naturo type "hello"` — System/COM error
- `naturo press enter` — System/COM error
- `naturo hotkey ctrl+c` — System/COM error
- `naturo scroll --direction down` — System/COM error
- `naturo move --coords 100 100` — System/COM error
- `naturo paste "Hello World"` — System/COM error
- `naturo drag --from-coords 100 100 --to-coords 200 200` — System/COM error

---

### ⚠️ 警告 (6)

1. **`app find --pid N` 忽略 NAME 参数** — `naturo app find dummy --pid 9408` 返回 explorer.exe (PID 9408)，NAME 参数被静默忽略。可能让用户困惑。

2. **`app find` 不支持中文名搜索** — `naturo app find 飞书` 返回 Not found，但 `naturo app find Feishu` 能找到。期望支持中文窗口标题/进程名匹配（设计原则 #3）。

3. **`learn [topic]` 只显示一行描述** — `naturo learn capture` 只输出 `capture: Capture screenshots...`，`naturo learn nonexistent_topic` 不报错而是显示 topic 列表。体验较差，教程内容为空。

4. **`list windows` 在 SSH 下返回空** — 即使系统有打开的窗口（飞书、微信、Chrome 等都在运行），SSH session 看不到。这可能是 Windows Session 隔离限制，但应在文档说明。

5. **`capture live --screen 0` 截取的是 1024x768** — 实际 Lead 分辨率应该更高，可能 SSH session 获取的虚拟屏幕分辨率有限。

6. **`find "*"` 被 shell glob 展开** — 在 cmd.exe 下 `naturo find * --depth 0` 报 `Got unexpected extra arguments`。这不是 naturo 的 bug（是 shell 行为），但对用户是个坑，可以在文档中提示用引号。

---

### 💡 建议 (8)

1. **【优先】移除或隐藏未实现的 app 子命令** — `switch/hide/unhide` 仍然暴露在 `app --help` 中且输出 "Not implemented yet"。要么实现它们，要么隐藏。这是设计原则 #1 的直接违反。

2. **【优先】统一 --json 模式的错误输出** — 目前 `see --json`、`find --json`、`menu-inspect --json`、`capture live --app X --json` 在错误/空结果时输出纯文本。规则应该是：**--json 模式下，任何输出都必须是合法 JSON**。

3. **【优先】修复 `app launch` 不验证进程存在** — launch 报告成功但进程并不存在。需要在 launch 后验证进程确实在运行。

4. **统一退出码语义** — `app find nonexistent` 返回 exit code 0（应该是 1？）；`wait --json` 超时返回 exit code 0（非 JSON 模式返回 1）。建议：找不到=1，参数错误=2，内部错误>2。

5. **数值参数边界校验** — `--count`、`--timeout`、`--days`、`--steps`、`--amount` 等数值参数应拒绝 ≤0 的值（或有明确语义）。

6. **中文路径支持** — 临时文件路径构造用了 `path + ".tmp.bmp"` 但在中文 Windows 编码环境下路径名会乱码。需要确保文件路径操作使用 Unicode。

7. **临时文件清理** — `capture live` 失败时 `.tmp.bmp` 文件残留。应在 finally 块中清理。

8. **`app list` 过滤** — 当前列出所有进程（包括 System Idle Process、svchost 等系统进程），用户体验更好的做法是只列有窗口的应用（Peekaboo 的行为）。
