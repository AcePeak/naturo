# QA Context — 项目记忆，QA Agent 必读

## 项目定位
- **Naturo**: Windows 桌面自动化工具，对标 macOS 的 Peekaboo
- **架构**: C++ Engine (naturo_core.dll) + Python 封装 + CLI
- **目标**: 成为 OpenClaw 生态 Windows 桌面自动化标准工具
- **接口对齐**: 和 Peekaboo 的 CLI 命令、参数、输出格式高度一致

## 当前状态
- **Phase 0-2.5**: 完成（See/Act/Deep Capabilities）
- **Phase 3**: 进行中（Stabilize — 错误处理/重试/等待/进程管理/缓存/Diff）
- **分支**: feat/phase3-stabilize

## 核心设计原则（Ace 确认）
1. **未实现的功能不暴露给用户** — 帮助里只显示能用的命令，没有 "Not implemented"
2. **输出格式和 Peekaboo 一致** — PNG 默认（不是 BMP），JSON schema 对齐
3. **中文 Windows 兼容** — 编码（GBK/UTF-8）、中文路径、中文窗口标题都要能处理
4. **帮助和实际行为始终一致** — 有 test_cli_consistency.py 守护
5. **错误信息面向用户** — 不暴露 traceback，给可读的错误消息和建议

## 已踩过的坑（历史 Bug）
这些是真实用户测试中发现的，QA 应该**验证已修复**并**举一反三**找同类问题：

### BUG-001: capture 输出 BMP 而非 PNG
- **现象**: `naturo capture live` 生成的文件虽然叫 .png 但实际是 BMP 格式
- **根因**: C++ DLL 原生只输出 BMP，Python 层没做格式转换
- **修复**: _convert_bmp() 用 Pillow 转换
- **举一反三**: 所有涉及文件输出的地方，是否都验证了实际文件格式？

### BUG-002: 中文 Windows 上 list windows 崩溃
- **现象**: `naturo list windows` 报 `'utf-8' codec can't decode byte 0xc3`
- **根因**: DLL 返回的字符串在中文 Windows 上是 GBK 编码，代码硬编码 UTF-8 解码
- **修复**: _decode_native() 先试 UTF-8 再 fallback 到系统 codepage
- **举一反三**: 所有从 DLL 读取字符串的地方是否都走了 _decode_native()？

### BUG-003: `naturo see --app "notepad"` 显示的是命令行的 UI 树
- **现象**: 指定了 --app 但看到的是终端窗口的元素
- **根因**: see 命令没把 --app 参数传给 backend，永远抓前台窗口
- **修复**: _resolve_hwnd() + 传递 app/window_title/hwnd 到 get_element_tree
- **举一反三**: 其他接受 --app 的命令（find、capture）是否也正确传递了？

### BUG-004: 未实现的命令暴露在 --help 中
- **现象**: `naturo --help` 列出 30+ 个命令，大部分打印 "Not implemented yet"
- **根因**: 所有 stub 命令都注册了，只是内部打印提示
- **修复**: 从 __init__.py 移除纯 stub 注册，混合组用 hidden=True
- **举一反三**: 新加的子命令是否有同样的问题？

### BUG-005: snapshot ID 暴露给普通用户
- **现象**: capture 输出 `Snapshot: 1773995768367-6317`，用户不知道这是什么
- **修复**: 普通输出只显示文件路径，snapshot ID 只在 --json 时输出
- **举一反三**: 其他命令是否也有对用户无意义的内部信息输出？

### BUG-006: `naturo` 命令不在 PATH 中
- **现象**: pip install -e . 安装后，用户敲 naturo 报 "不是内部或外部命令"
- **根因**: Python Scripts 目录不在 PATH
- **提醒**: 这是安装体验问题，未来打包时需解决

## 测试环境
- **Lead (Win11-Home)**: 中文 Windows 11, Intel Xeon E5-2686 v4, 32GB RAM
- **SSH**: llfac@100.94.85.44 (通过 Tailscale)
- **Python**: 3.14.2
- **DLL**: naturo/bin/naturo_core.dll（CI 编译，已 SCP 到 Lead）
- **SSH 限制**: 无桌面 session，capture/see/click/type 等交互命令会返回 System/COM error
- **Git 限制**: Lead 上 GitHub 连接不稳定，用 SCP 同步文件

## Peekaboo 参考
- 默认截图格式: PNG
- 错误码: StandardErrorCode (APP_NOT_FOUND, ELEMENT_NOT_FOUND, TIMEOUT 等)
- 重试策略: RetryPolicy (standard/aggressive/conservative/no_retry)
- Wait 轮询间隔: 100ms
- App 命令: launch/quit/relaunch/list/find
- 错误输出: 有 category, code, message, suggested_action, context

## 测试重点（当前 Phase 3）
1. 错误处理：每种错误类型是否返回正确的 code 和 message
2. Wait/Retry：超时行为是否准确，重试间隔是否正确
3. App 命令：launch/quit/find 是否正常工作
4. JSON 输出：每个命令的 --json 是否返回可解析、字段完整的 JSON
5. 编码：所有涉及中文的场景（窗口标题、进程名、文件路径）
6. 文件格式：所有文件输出验证 magic bytes
