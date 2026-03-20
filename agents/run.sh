#!/bin/bash
# Naturo Agent Runner
# 定期启动 QA 和 Dev agent，读取项目上下文，自主工作
#
# Usage:
#   bash agents/run.sh           # 跑所有角色
#   bash agents/run.sh qa        # 只跑 QA
#   bash agents/run.sh dev       # 只跑 Dev

set -euo pipefail
NATURO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG_DIR="$NATURO_DIR/.work/logs"
mkdir -p "$LOG_DIR"

log() {
  echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG_DIR/agent-runner.log"
}

# PAUSE 检查
if [ -f "$NATURO_DIR/agents/PAUSE.md" ]; then
  log "PAUSED — 见 agents/PAUSE.md"
  exit 0
fi

run_agent() {
  local role=$1
  local soul_file="$NATURO_DIR/agents/$role/SOUL.md"
  
  if [ ! -f "$soul_file" ]; then
    log "ERROR: $soul_file not found"
    return 1
  fi

  # 读取上下文文件
  local state=$(cat "$NATURO_DIR/agents/STATE.md" 2>/dev/null || echo "无")
  local rules=$(cat "$NATURO_DIR/agents/RULES.md" 2>/dev/null || echo "无")
  local soul=$(cat "$soul_file" 2>/dev/null || echo "无")
  local bugs=$(cat "$NATURO_DIR/.work/bugs.md" 2>/dev/null || echo "无")
  local roadmap=$(cat "$NATURO_DIR/docs/ROADMAP.md" 2>/dev/null || echo "无")
  local qa_context=$(cat "$NATURO_DIR/tests/QA_CONTEXT.md" 2>/dev/null || echo "无")

  log "Starting $role agent..."

  local task="你是 Naturo 的 $role Agent。读完以下上下文后，自主判断该做什么，开始工作。

## 项目状态
$state

## 通用规则
$rules

## 你的职责
$soul

## Bug 清单
$bugs

## 产品路线图（摘要）
当前在 Phase 3 (Stabilize)，目标是 bug 清零 + E2E 验收通过。
详见 $NATURO_DIR/docs/ROADMAP.md

## QA 上下文（已知问题和测试环境）
$qa_context

---

开始工作。完成后更新 agents/STATE.md 并通过飞书群通知进展。
飞书通知用 message 工具: channel=feishu, target=user:ou_5f9d6648ee89d4186ff0b8912d56e33d"

  # 用 openclaw subagent 方式运行（如果可用），否则直接调用
  if command -v openclaw &>/dev/null; then
    openclaw agent --message "$task" >> "$LOG_DIR/${role}-$(date +%Y%m%d).log" 2>&1 &
    log "$role agent launched (PID: $!)"
  else
    log "ERROR: openclaw not found, cannot run agent"
    return 1
  fi
}

# 决定跑哪些角色
roles="${1:-qa dev}"

for role in $roles; do
  run_agent "$role"
  sleep 5  # 错开启动
done

log "Agent run complete"
