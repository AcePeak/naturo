# QA Round 11 Report — QA-Mariana
**Date:** 2026-03-23 00:12 (Asia/Shanghai)
**Version:** naturo 0.2.0
**Test Machine:** Naturobot@100.113.29.45 (compile machine, SSH)

## 产品审视

当前 v0.2.0 已发布，核心命令（see, capture, find, list, app, snapshot, mcp）基本功能正常。所有历史 bug issues 已关闭。v0.2.0 milestone 剩余 4 个 open issues（#109 naturo get, #101 selector spec, #37 integration tests, #28 auto-routing）。

**最大质量风险：CI 红了。**

## 🔴 CI 状态：RED

最新 commit `6d7f14d`（test: add method override tests）导致全平台 CI 失败。

**根因：** `tests/test_method_override.py` 第 11 行 `from naturo.cli.interaction import VALID_METHODS` 在 CI 环境导入失败。`VALID_METHODS` 在源码 `naturo/cli/interaction.py:19` 确实存在，本地也能导入，但 CI 三个平台（Ubuntu/macOS/Windows）全部 `ImportError`。

**可能原因：** CI 的 `pip install -e .` 可能缓存了旧的 egg-info/build，导致导入路径指向了不包含 `VALID_METHODS` 的旧版本模块。

**严重度：P0 — 阻断所有 CI 测试。**

## Dev Completions 验证

无待验证的 `status:done` issues。

## 测试结果

### L0 冒烟测试

| 测试项 | 结果 | 备注 |
|--------|------|------|
| `naturo --version` | ✅ | 0.2.0 |
| `naturo --help` | ✅ | 22 个命令正常列出 |
| `naturo see --json` | ✅ | 无窗口时返回清晰错误 WINDOW_NOT_FOUND |
| `naturo capture live --json` | ✅ | 截图成功 1024x768 |
| `naturo list screens --json` | ✅ | 正确返回 1024x768, 96 DPI |
| `naturo list windows --json` | ✅ | SSH 下正确返回空+警告 |
| `naturo app list` | ✅ | 正确返回空列表 |
| `naturo find "test" --json` | ✅ | 正确返回 WINDOW_NOT_FOUND |
| `naturo snapshot list --json` | ✅ | 正常 |
| `naturo snapshot clean --all --json` | ✅ | 清理 29 个旧快照 |
| `naturo mcp tools --json` | ✅ | 51 个 MCP tools 正常列出 |
| `naturo menu-inspect --json` | ✅ | 正确返回 NO_MENU_ITEMS |
| `naturo window list --json` | ✅ | SSH 下正确返回空 |

### 发现的问题

#### ISSUE-1: `naturo list apps` vs `naturo app list` 行为不一致 (P1)
- `naturo list apps` → 返回 NOT_IMPLEMENTED 错误
- `naturo app list` → 正常工作，返回结果
- **影响：** 用户看到 `list` 命令有 `screens` 和 `windows` 子命令，自然会尝试 `list apps`，结果被告知未实现。但实际上 `app list` 是可用的。违反最小惊讶原则。
- **建议：** 要么让 `list apps` 委托到 `app list`，要么移除 `list apps` 的 NOT_IMPLEMENTED 响应改为提示用户使用 `naturo app list`。

#### ISSUE-2: 交互命令 SSH 下错误信息不友好 (P1)
- `naturo click --coords 100 100` → `"mouse_move: System/COM error"`
- `naturo type "hello"` → `"key_type: System/COM error"`
- `naturo press enter` → `"key_press('enter'): System/COM error"`
- `naturo hotkey ctrl+a` → `"key_hotkey(('ctrl', 'a')): System/COM error"`
- `naturo scroll down` → `"mouse_scroll: System/COM error"`
- **对比：** `naturo list windows` 能正确检测并提示 "no interactive desktop session detected — running via SSH or service?"
- **影响：** 用户通过 SSH 使用 naturo（常见的 AI agent 场景），交互命令失败时只看到 "System/COM error"，完全不知道怎么解决。
- **建议：** 复用 `see`/`list windows` 的桌面检测逻辑，在交互命令执行前检查，给出清晰的错误信息。

#### ISSUE-3: CI RED — test_method_override.py 导入失败 (P0)
- 详见上文 CI 状态章节。

## 质量评估

### 当前状态：🟡 基本可用，有瑕疵
- **核心功能（截图、元素检查、列表）**：稳定，错误处理良好
- **MCP 集成**：51 个 tools，覆盖全面
- **错误信息质量**：参差不齐 — `see`/`find`/`list` 的错误信息优秀（有 suggested_action），但交互命令的错误信息糟糕
- **CI**：当前红了，阻断质量保证流程

### 离发布还差什么
1. CI 必须先修绿（P0）
2. 交互命令的错误信息需要统一（P1）
3. `list apps` 入口不一致需要解决（P1）
4. v0.2.0 里 #109（naturo get）是 Ace 标的 P0 enhancement，核心缺失功能

### Top 3 改进建议
1. **修 CI**（紧急）— `test_method_override.py` 的导入问题，可能需要在 CI workflow 里加 `pip install -e . --no-build-isolation` 或清缓存
2. **统一错误体验** — 所有命令在无桌面环境下应给出一致的、有指导性的错误信息
3. **命令入口统一** — `list` 子命令和 `app`/`window` 子命令的功能重叠需要整理

### 风险预警
- CI 红 = 后续所有 commit 无法验证，质量下降风险高
- SSH 下交互命令的糟糕错误信息会影响 AI agent 集成体验（naturo 的核心场景之一）

## 自检
1. ✅ 本轮做了 L0 冒烟 + 部分 L1 功能测试
2. ✅ 在真机 SSH 环境测试
3. ✅ 以用户视角（不看源码）测试了命令
4. ✅ 发现的问题追到了设计层面（错误处理一致性）
5. 本轮验证了"对不对" — 错误信息质量和命令入口一致性
6. 新用户 pip install naturo 后，如果在有桌面的环境下使用体验尚可；SSH 环境下交互命令体验差
