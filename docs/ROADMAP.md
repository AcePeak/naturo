# Roadmap

## Phase 0 — Project Skeleton ✅
- Project structure (C++ core + Python wrapper)
- CI/CD pipeline (GitHub Actions)
- Version function + basic CLI
- TDD infrastructure
- Cross-platform backend abstraction layer

**Checkpoint:** CI green, `naturo version` works, backend auto-detection works on all platforms.

## Phase 1 — See ✅
- Screen capture (GDI → Pillow PNG conversion)
- Window enumeration
- UI tree inspection (UIA)
- Element attributes (name, role, bounds, state)

**CLI commands:** `capture`, `list`, `see`

## Phase 1.5 — Snapshot System ✅
- Snapshot creation, storage, retrieval
- Screenshot + UI tree bundling
- Snapshot listing and cleanup

## Phase 2 — Act ✅
- Mouse input (click, double-click, right-click, drag)
- Keyboard input (type text, press keys, combos)
- Element finding by selector
- Coordinate-based and element-based actions

**CLI commands:** `click`, `type`, `press`, `find`, `hotkey`, `scroll`, `drag`, `move`, `paste`

## Phase 2.5 — Deep Capabilities ✅
- Annotated screenshots (numbered bounding boxes)
- Element search/query (fuzzy match, role filter)
- UI hierarchy (parent_id, children linkage)
- Keyboard shortcut discovery
- Menu bar traversal

## Phase 3 — Stabilize ✅
- Error handling framework (Peekaboo-aligned error codes)
- Wait/retry strategies (100ms polling, exponential backoff)
- Process management (launch/quit/relaunch/find)
- Element cache (TTL-based, auto-invalidation)
- UI tree diff
- CLI consistency test (no stubs exposed)
- 40 bugs found and fixed through QA/Dev agent loop
- 700+ tests

## Phase 3.5 — Window Management (补齐 Peekaboo 对等能力)

**Goal**: 实现完整的窗口操作，对齐 Peekaboo 的 `window` 命令组。

**Prerequisites**: Phase 2 (Act) + Phase 3 (Stabilize)

| Step | Deliverable | Status |
|------|------------|--------|
| 3.5.1 | **Window Focus** — `naturo window focus --app "Notepad"` / `--hwnd 12345` / `--window-title "文档"` | ✅ Done |
| 3.5.2 | **Window Close** — `naturo window close --app "Notepad"` 优雅关闭（WM_CLOSE），`--force` 强制终止 | ✅ Done |
| 3.5.3 | **Window Minimize/Maximize/Restore** — `naturo window minimize/maximize/restore --app "Notepad"` | ✅ Done |
| 3.5.4 | **Window Move** — `naturo window move --app "Notepad" --x 100 --y 100` | ✅ Done |
| 3.5.5 | **Window Resize** — `naturo window resize --app "Notepad" --width 800 --height 600` | ✅ Done |
| 3.5.6 | **Window Set Bounds** — 一次性设置位置+大小，对齐 Peekaboo `window set-bounds` | ✅ Done |
| 3.5.7 | **App Hide/Unhide** — 最小化/恢复应用所有窗口 | ✅ Done |
| 3.5.8 | **App Switch** — 切换到目标应用（SetForegroundWindow） | ✅ Done |
| 3.5.9 | **MCP Window Tools** — 上述能力暴露到 MCP server | ✅ Done |
| 3.5.10 | **Window List** — `naturo window list` 带过滤器 (--app/--pid/--process-name) | ✅ Done |
| 3.5.11 | **Tests** — 105 个窗口管理测试 (CLI + backend + MCP + JSON 一致性) | ✅ Done |

**Implementation**: C++ DLL 层用 Win32 API（ShowWindow, MoveWindow, SetWindowPos, SetForegroundWindow）。Python 层通过 bridge.py 调用。

**Checkpoint:** `naturo window close --app "Notepad"` 可以关闭记事本。`naturo window move --app "Chrome" --x 0 --y 0 && naturo window resize --app "Chrome" --width 1920 --height 1080` 可以排列窗口。

## Phase 4 — AI Integration

**Goal**: 让 AI agent 能端到端驱动 Windows 应用。

| Step | Deliverable | Status |
|------|------------|--------|
| 4.1 | **MCP Server** — 29 tools, stdio/sse/streamable-http transport | ✅ Done |
| 4.2 | **Screenshot → AI Vision** — 截图发给 AI 分析 UI 元素，返回结构化描述 | 🔜 |
| 4.3 | **Natural Language Element Finding** — `naturo find "the save button"` 用 AI 理解自然语言 | 🔜 |
| 4.4 | **Agent Command** — `naturo agent "打开记事本，输入Hello World，保存到桌面"` 多步骤自动执行 | ✅ Done |
| 4.5 | **Action Recording** — 录制用户操作序列，生成可回放的脚本 | 🔜 |
| 4.6 | **Action Replay** — 回放录制的操作序列，支持参数化 | 🔜 |
| 4.7 | **Agent-friendly Error Messages** — 错误信息包含恢复建议，帮助 AI 自我纠正 | ✅ Done |
| 4.8 | **Multi AI Provider** — Anthropic / OpenAI / Ollama / 自定义，类似 Peekaboo Tachikoma | ✅ Done |

**Checkpoint:** `naturo agent "打开计算器，计算 123*456，截图结果"` 可以端到端完成。

## Phase 4.5 — Dialog & System Integration

**Goal**: 处理系统对话框和常见 UI 模式。

| Step | Deliverable | Status |
|------|------------|--------|
| 4.5.1 | **Dialog Detection** — 自动检测文件选择器、消息框、确认框 | 🔜 |
| 4.5.2 | **Dialog Interaction** — `naturo dialog accept/dismiss/fill` | 🔜 |
| 4.5.3 | **Clipboard Enhanced** — `naturo clipboard get/set` 命令（已有 backend，需暴露 CLI） | ✅ Done |
| 4.5.4 | **Taskbar Interaction** — 任务栏 pin/unpin/click | 🔜 |
| 4.5.5 | **System Tray** — 系统托盘图标交互 | 🔜 |
| 4.5.6 | **Open Command** — `naturo open <url/file>` 用默认应用打开 | ✅ Done |

## Phase 5 — Complete (生产级 + 自然机器人差异化引擎)

**Goal**: 实现自然机器人 C++ 引擎的深度能力，这是 Naturo 相比纯 Python 工具的核心竞争力。

### 5A — Multi-Monitor & DPI

| Step | Deliverable | Status |
|------|------------|--------|
| 5A.1 | **Multi-Monitor Capture** — `naturo capture --screen 1` 指定显示器 | 🔜 |
| 5A.2 | **DPI/Scaling Awareness** — 正确处理 125%/150%/200% 缩放下的坐标和截图 | 🔜 |
| 5A.3 | **Virtual Desktop** — Windows 10/11 虚拟桌面切换和窗口管理 | 🔜 |

### 5B — 自然机器人引擎移植（核心差异化）

| Step | Deliverable | 来源 | Status |
|------|------------|------|--------|
| 5B.1 | **MSAA / IAccessible** — 传统可访问性 API，覆盖 UIA 不支持的老应用 | Naturobot_Client_Engine | 🔜 |
| 5B.2 | **IAccessible2** — Firefox/Thunderbird 等 IA2 应用支持 | Naturobot_Client_Engine | 🔜 |
| 5B.3 | **Java Access Bridge** — Java/Swing/AWT 应用自动化 | Naturobot_Client_Engine | 🔜 |
| 5B.4 | **SAP GUI Scripting** — SAP ERP 应用自动化 | Naturobot_Client_Engine | 🔜 |
| 5B.5 | **硬件级键盘 (Phys32)** — 绕过 SendInput 检测的底层键盘输入，适用于游戏/安全软件 | Naturobot_Client_Engine | 🔜 |
| 5B.6 | **MinHook 注入** — 函数钩子，拦截/修改 Windows API 调用 | Naturobot_Client_Engine | 🔜 |
| 5B.7 | **UIA 缓存优化** — 批量获取属性、减少跨进程 COM 调用、CacheRequest 模式 | Naturobot_Client_Engine | 🔜 |
| 5B.8 | **Chrome Native Host** — 通过 Chrome DevTools Protocol 直接操作浏览器 DOM | Naturobot_Client_Engine | 🔜 |

### 5C — Enterprise Features

| Step | Deliverable | Status |
|------|------------|--------|
| 5C.1 | **Excel COM Automation** — 读写单元格、运行宏、创建图表 | 🔜 |
| 5C.2 | **Windows Registry** — 读写注册表 | 🔜 |
| 5C.3 | **Windows Service** — 管理 Windows 服务 | 🔜 |
| 5C.4 | **Electron/CEF App Support** — 识别 Electron 应用并提供 DOM 级操作 | 🔜 |

### 5D — Packaging

| Step | Deliverable | Status |
|------|------------|--------|
| 5D.1 | **Embedded Python Runtime** — 内置 Python 3.12 嵌入式包（~40MB），用户脚本运行环境 | 🔜 |
| 5D.2 | **Standalone Executable** — Nuitka/PyInstaller 打包 naturo.exe | 🔜 |
| 5D.3 | **User Script Runner** — `naturo run my_script.py` 用内置环境执行用户脚本 | 🔜 |

**Checkpoint:** Java 应用（如 IntelliJ IDEA）可以被自动化。SAP GUI 可以被操作。游戏内输入不被检测。

## Phase 5.1 — Open Source Launch

**Goal**: Go public with maximum impact.

**Pre-launch:**

| Step | Deliverable |
|------|------------|
| 5.1.1 | Branch protection (require PR + CI) |
| 5.1.2 | CONTRIBUTING.md |
| 5.1.3 | CODE_OF_CONDUCT.md |
| 5.1.4 | Issue/PR templates |
| 5.1.5 | README hero GIF (Notepad E2E demo) |
| 5.1.6 | README badges |
| 5.1.7 | First PyPI release (`pip install naturo`) |
| 5.1.8 | OpenClaw skill published to ClawHub |
| 5.1.9 | 代码签名证书 + CI 集成 |
| 5.1.10 | npm 包 (`npx naturo mcp`) |

**Launch:**

| Step | Deliverable |
|------|------------|
| 5.1.11 | Flip repo to public |
| 5.1.12 | LinkedIn / Reddit / Twitter / HN / Discord announcements |
| 5.1.13 | "How Naturo Works" blog post |
| 5.1.14 | Submit to awesome-python, awesome-automation |
| 5.1.15 | Demo videos (YouTube + Bilibili) |

## Phase 6 — macOS Backend

**Goal**: Full macOS support via Peekaboo CLI wrapper.

| Step | Deliverable |
|------|------------|
| 6.1 | Peekaboo CLI detection + subprocess wrapper |
| 6.2 | capture/list/see via Peekaboo |
| 6.3 | click/type/press/hotkey via Peekaboo |
| 6.4 | app/window/menu via Peekaboo |
| 6.5 | dock/space mapping |
| 6.6 | CI: macOS runner integration tests |
| 6.7 | Fallback: pyobjc for Peekaboo-free environments |

## Phase 7 — Linux Backend

**Goal**: Linux (X11 + Wayland) support.

| Step | Deliverable |
|------|------------|
| 7.1 | X11: xdotool + python-xlib |
| 7.2 | AT-SPI2 element inspection |
| 7.3 | Screenshot via Xlib / dbus portal |
| 7.4 | Wayland: ydotool + wlr protocols |
| 7.5 | CI: Ubuntu + xvfb UI tests |
| 7.6 | GNOME + KDE compatibility |

## Phase 8 — National OS & Enterprise

**Goal**: UOS, Kylin, openEuler support.

| Step | Deliverable |
|------|------------|
| 8.1 | DDE (Deepin Desktop) compatibility |
| 8.2 | Kylin adapters |
| 8.3 | Self-hosted CI runner |
| 8.4 | Enterprise recording/playback engine |
| 8.5 | Enterprise visual regression testing |

## Phase 9 — Strategic Outreach

**Goal**: Build ecosystem relationships (after 500+ stars).

| Step | Deliverable |
|------|------------|
| 9.1 | Peekaboo author collaboration |
| 9.2 | OpenClaw team — recommended Windows tool |
| 9.3 | Conference talk (PyCon/EuroPython) |
| 9.4 | RPA/testing community partnerships |
| 9.5 | Peekaboo integration — official Windows counterpart |

---

## TDD Requirements (All Phases)

1. Write failing test → 2. Implement → 3. Refactor → 4. QA/PD/Security review

## Agent Development Loop

- **Dev Agent**: 每 15 分钟巡检，修 bug + 实现功能
- **QA Agent**: 每 30 分钟巡检，验证 + 自发现测试
- 协同通过 `agents/STATE.md` + `.work/bugs.md` + 飞书群
