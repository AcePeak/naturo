# QA 全覆盖测试计划 — Round Full

> 目标：naturo --help 列出的每条命令 × 每个参数，正常值/边界值/错误值全覆盖

## 测试环境
- Windows Lead: ssh llfac@100.94.85.44
- 代码同步: scp 或 rsync（GitHub 不通时）
- 测试应用: Notepad (记事本)

## 命令清单 (18 commands)

### 1. version
- `naturo --version` → 输出版本号

### 2. app launch
- ✅ `naturo app launch notepad` → 启动记事本
- ❌ `naturo app launch nonexistent_xyz` → 报错 (BUG-013)
- ❌ `naturo app launch ""` → 报错
- ❌ `naturo app launch` (无参数) → usage 提示

### 3. app quit
- ✅ `naturo app quit notepad` → 关闭记事本
- ❌ `naturo app quit nonexistent` → 报错
- ✅ `naturo app quit notepad --force` → 强制关闭
- ❌ `naturo app quit ""` → 报错

### 4. app find
- ✅ `naturo app find notepad` → 找到
- ❌ `naturo app find nonexistent` → exit code 1 (BUG-008 ✅)
- ❌ `naturo app find ""` → 报错 (BUG-009 ✅)
- ✅ `naturo app find notepad --json` → JSON 输出
- ✅ PID 查找: `naturo app find --pid <PID>`

### 5. app list
- ✅ `naturo app list` → 列出进程
- ✅ `naturo app list --json` → JSON 输出

### 6. app relaunch
- ✅ `naturo app relaunch notepad` → 重启记事本
- ❌ `naturo app relaunch nonexistent` → 报错 (BUG-018)

### 7. capture live
- ✅ `naturo capture live` → 截全屏
- ✅ `naturo capture live --path test.png` → 保存到文件
- ✅ `naturo capture live --app notepad` → 截特定窗口
- ❌ `naturo capture live --app nonexistent` → 报错
- ✅ `naturo capture live --path test_中文.png` → 中文路径 (BUG-017)
- ✅ `naturo capture live --json` → JSON 输出
- ❌ `naturo capture live --app nonexistent --json` → JSON 错误 (BUG-015 ✅)

### 8. click
- ✅ `naturo click --coords 500 300` → 点击坐标
- ✅ `naturo click --coords 500 300 --double` → 双击
- ✅ `naturo click --coords 500 300 --right` → 右键
- ❌ `naturo click --coords -1 -1` → 边界
- ❌ `naturo click --coords abc def` → 类型错误
- ✅ `naturo click --on "Edit"` → 点击元素
- ✅ `naturo click --id "button_ok"` → ID 点击
- ✅ `naturo click --app notepad --coords 100 100` → 指定窗口
- ❌ `naturo click` (无参数) → usage 或报错
- ✅ `naturo click --input-mode hardware --coords 500 300`
- ✅ `naturo click --input-mode hook --coords 500 300`
- ✅ `naturo click --json --coords 500 300` → JSON 输出

### 9. diff
- ✅ `naturo diff --window "Notepad" --interval 2` → 对比变化
- ❌ `naturo diff --window nonexistent` → 报错
- ✅ `naturo diff --snapshot snap1 --snapshot snap2` → 两快照对比
- ❌ `naturo diff --snapshot nonexistent` → 报错
- ✅ `naturo diff --json --window "Notepad" --interval 1` → JSON

### 10. drag
- ✅ `naturo drag --from-coords 100 100 --to-coords 500 300` → 拖拽
- ❌ `naturo drag` (无参数) → 报错
- ✅ `naturo drag --from-coords 100 100 --to-coords 500 300 --duration 1.0`
- ✅ `naturo drag --from-coords 100 100 --to-coords 500 300 --steps 20`
- ❌ `naturo drag --from-coords 100 100` (缺 to) → 报错

### 11. find
- ✅ `naturo find "Save"` → 模糊搜索
- ✅ `naturo find "Button:Save"` → role + name
- ✅ `naturo find "role:Edit"` → 按 role
- ✅ `naturo find "*" --actionable` → 可操作元素
- ✅ `naturo find "Save" --depth 3` → 限制深度
- ✅ `naturo find "Save" --limit 5` → 限制数量
- ❌ `naturo find ""` → 报错
- ❌ `naturo find "Save" --depth 0` → 边界
- ❌ `naturo find "Save" --depth -1` → 边界
- ✅ `naturo find "Save" --json` → JSON 输出

### 12. hotkey
- ✅ `naturo hotkey ctrl+c` → 复制
- ✅ `naturo hotkey alt+f4` → 关闭
- ❌ `naturo hotkey ""` → 报错
- ❌ `naturo hotkey invalidkey` → 报错
- ✅ `naturo hotkey --keys ctrl --keys shift --keys z` → 多键
- ✅ `naturo hotkey ctrl+c --json` → JSON

### 13. learn
- ✅ `naturo learn` → 概览
- ✅ `naturo learn capture` → 特定主题
- ❌ `naturo learn nonexistent_topic` → 合理处理

### 14. list windows
- ✅ `naturo list windows` → 列出窗口
- ✅ `naturo list windows --json` → JSON (BUG-012 ✅)

### 15. menu-inspect
- ✅ `naturo menu-inspect` → 当前窗口菜单
- ✅ `naturo menu-inspect --app notepad` → 特定应用
- ✅ `naturo menu-inspect --flat` → 扁平模式
- ❌ `naturo menu-inspect --app nonexistent` → 报错
- ✅ `naturo menu-inspect --json` → JSON

### 16. move
- ✅ `naturo move --coords 500 300` → 移动鼠标
- ❌ `naturo move` (无参数) → 报错
- ✅ `naturo move --to "Edit"` → 移到元素
- ✅ `naturo move --duration 0.5 --coords 500 300`

### 17. paste
- ✅ `naturo paste "Hello World"` → 粘贴
- ✅ `naturo paste --file test.txt` → 从文件
- ✅ `naturo paste "test" --restore` → 恢复剪贴板
- ❌ `naturo paste` (无参数无 file) → 报错
- ❌ `naturo paste --file nonexistent.txt` → 报错

### 18. press
- ✅ `naturo press enter` → 按键
- ✅ `naturo press tab --count 3` → 多次
- ❌ `naturo press --count 0` → 报错 (BUG-019 ✅)
- ❌ `naturo press --count -1` → 报错 (BUG-019 ✅)
- ❌ `naturo press invalidkey` → 报错
- ✅ `naturo press enter --delay 100` → 延迟
- ✅ `naturo press enter --json` → JSON

### 19. scroll
- ✅ `naturo scroll` → 默认下滚
- ✅ `naturo scroll -d up -a 5` → 上滚 5 格
- ✅ `naturo scroll -d left` → 左滚
- ✅ `naturo scroll -d right` → 右滚
- ❌ `naturo scroll -d invalid` → 报错
- ❌ `naturo scroll -a 0` → 边界
- ❌ `naturo scroll -a -1` → 边界
- ✅ `naturo scroll --json` → JSON

### 20. see
- ✅ `naturo see` → 当前窗口 UI 树
- ✅ `naturo see --app notepad` → 特定应用
- ✅ `naturo see --depth 3` → 限制深度
- ✅ `naturo see --mode full` / `interactive` / `fast`
- ✅ `naturo see --annotate` → 带标注截图
- ✅ `naturo see --path screenshot.png` → 保存截图
- ❌ `naturo see --depth 0` → 边界
- ❌ `naturo see --depth -1` → 边界
- ❌ `naturo see --app nonexistent` → 报错
- ✅ `naturo see --json` → JSON (BUG-014 ✅)
- ✅ `naturo see --no-snapshot` → 不保存快照

### 21. snapshot list / clean
- ✅ `naturo snapshot list` → 列出快照
- ✅ `naturo snapshot clean` → 清理
- ✅ `naturo snapshot clean --days 7` → 按天数
- ❌ `naturo snapshot clean --days 0` → 边界
- ❌ `naturo snapshot clean --days -1` → 报错 (BUG-021 ✅)

### 22. type
- ✅ `naturo type "Hello World"` → 输入文本
- ✅ `naturo type "Hello" --return` → 回车
- ✅ `naturo type "test" --tab 2` → Tab
- ✅ `naturo type "test" --escape` → Esc
- ✅ `naturo type "test" --delete` → 先删再输
- ✅ `naturo type "test" --clear` → 全选删除再输
- ✅ `naturo type "test" --profile human --wpm 60`
- ❌ `naturo type ""` → 空字符串
- ❌ `naturo type` (无参数) → 报错
- ✅ `naturo type "test" --delay 50`
- ✅ `naturo type "test" --input-mode hardware`
- ✅ `naturo type "test" --json` → JSON

### 23. wait
- ✅ `naturo wait --window "Notepad" --timeout 5` → 等窗口
- ✅ `naturo wait --element "Button:Save" --timeout 1` → 等元素
- ✅ `naturo wait --gone "Dialog:Loading" --timeout 1` → 等消失
- ❌ `naturo wait --timeout -1` → 报错 (BUG-020 ✅)
- ❌ `naturo wait` (无参数) → 报错
- ✅ `naturo wait --json --element "Save" --timeout 1` → JSON (BUG-016)
- ✅ `naturo wait --interval 0.5 --window "Notepad" --timeout 3`

## 全局参数（每个支持的命令都测）
- `--json` / `-j` → JSON 输出格式
- `--verbose` / `-v` → 详细日志
- `--log-level trace/debug/info/warning/error`
- `--help` → 帮助信息

## 测试总计
约 **130+ 测试用例**
