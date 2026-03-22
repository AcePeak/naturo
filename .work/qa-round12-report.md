# QA Round 12 Report — QA-Mariana
**Date:** 2026-03-23 01:47 (Asia/Shanghai)
**Version:** naturo 0.2.0 (commit f8d275c)
**Test Machine:** Naturobot@100.113.29.45 (compile machine, SSH)

## 产品审视

v0.2.0 已发布，CI 已恢复绿色（commit f8d275c 修复了 CI import error）。无 `status:done` 待验证 issues。当前 open issues 全部为 enhancement/feature（#109 naturo get, #101-106 unified selector, #53-96 roadmap）。

**最大质量风险：SSH 环境下 GUI 命令的错误信息仍不清晰（#99 修复不完整）。**

## Dev Completions 验证

无 `status:done` issues 待验证。所有 closed issues 已有 `verified` 标签或为 task/doc 类型。

## CI 状态：🟢 GREEN

最新 CI run (commit f8d275c) 全平台通过。Round 11 报告的 CI 红已修复。

## 测试结果

### L0 冒烟测试

| 测试项 | 结果 | 备注 |
|--------|------|------|
| `--version` | ✅ | 0.2.0 |
| `--help` | ✅ | 22 commands listed |
| `list screens --json` | ✅ | 1024x768, 96 DPI, scale 1.0 |
| `list windows --json` | ⚠️ | 返回空 + SSH warning（expected） |
| `capture live --json` | ✅ | 截图成功，1024x768 |
| `app list --json` | ✅ | 返回空（SSH 无窗口，expected） |
| `app list --all --json` | ✅ | 97 processes |
| `app launch notepad --json` | ✅ | PID 15820, launched |
| `app --help` | ✅ | 9 subcommands |
| `find --help` | ✅ | 正常 |
| `see --help` | ✅ | 正常 |

### L1 功能测试 — 错误处理 & 边界值

| 测试项 | 结果 | Issue |
|--------|------|-------|
| `click --coords 0 0 --json` | ❌ "System/COM error", exit 1 | #113 |
| `click --coords 100 100 --json` | ❌ "System/COM error", exit 1 | #113 |
| `click --id nonexistent --json` | ⚠️ 正确报错但 exit code=0 | #115 |
| `hotkey ctrl+c --json` | ❌ "System/COM error" | #113 |
| `press enter --json` | ❌ "System/COM error" | #113 |
| `find "*" --json` | ❌ Shell glob expansion 崩溃 | #112 |
| `find "Save" --json` | ✅ WINDOW_NOT_FOUND（expected in SSH） |
| `see --json` | ✅ WINDOW_NOT_FOUND（expected） |
| `list apps --json` | ❌ NOT_IMPLEMENTED | #114 |
| `capture --json` | ✅ Error: No such option (子命令结构正确) |

### 新发现 Bug

| Issue | 标题 | 严重度 |
|-------|------|--------|
| #112 | `find` wildcard `"*"` query gets shell-expanded on Windows | P1 |
| #113 | #99 fix incomplete: SSH + active RDP still gets "System/COM error" | P1 |
| #114 | `list apps` returns NOT_IMPLEMENTED but `app list` works | P2 |
| #115 | `click --id` returns exit code 0 on failure | P2 |

## 产品质量评估

**当前水平：L0 冒烟基本通过，但 SSH 使用场景有明显缺陷。**

v0.2.0 作为 "Eyes+Hands" 聚焦版本，核心命令（see, capture, find, app）结构清晰，JSON 输出规范。CI 绿。但在 SSH 远程操作这个关键场景下，错误信息质量还不达标。

**离发布差距：**
- 核心功能（截图、元素查看）可用 ✅
- 命令结构清晰、--help 完善 ✅
- SSH 远程使用体验不佳 ⚠️（#113 是关键）
- 命令一致性有小问题 ⚠️（#114, #115）
- `naturo get`（#109）缺失——无法读取元素值是大缺口

## Top 3 改进建议

1. **修复 #113（SSH 桌面检测）** — 这是用户通过 SSH 操作远程 Windows 最常见的场景。当前错误信息完全无法帮助排查，应该检测当前 session 而非全局 explorer 状态。

2. **完成 #109（naturo get）** — 能看不能读是重大能力缺口。AI Agent 需要 see→get→click 完整流程才能做决策。

3. **统一退出码逻辑** — success:false 必须 exit 1。这对 AI Agent 和脚本集成至关重要。

## 风险预警

1. **#113 会在所有 SSH/CI 测试中反复出现** — 任何通过 SSH 使用 naturo 的用户都会碰到这个问题。考虑到 naturo 面向 AI Agent，SSH 是极其常见的使用方式。
2. **命令重复（list apps vs app list）** — 随着命令增多，如果不统一命名策略，用户困惑会指数增长。
3. **Windows shell quoting** — #112 只是冰山一角。任何包含特殊字符的参数（空格、引号、通配符）都可能在 cmd.exe/PowerShell 中出问题。需要系统性地审视所有接受自由文本的参数。

## QA 自检

1. ✅ 本轮做了 L1 功能测试
2. ✅ 在真机（SSH）上测试
3. ✅ 用"装傻"视角测试了常见用法
4. ✅ 发现的 bug 追到了设计层面（#113 的检测逻辑、#114 的命令命名一致性）
5. ✅ 验证了"对不对"而非仅"能不能跑"
6. ❌ 新用户 pip install naturo 后在 SSH 环境会遇到困惑 → 已报 P1
