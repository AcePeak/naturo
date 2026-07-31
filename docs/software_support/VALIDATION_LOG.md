# Naturo Software-Support Validation Log

Complete record of **every software window** we validate — success **and** failure.
See the acceptance gate in [`README.md`](README.md). Iron laws (do not violate):

1. **All operations go through naturo** (`naturo see`/`click`/`type`, `mcp__naturo__*`). Never
   raw PowerShell PostMessage/SendInput, never winget (install via the app's own store, driven by
   naturo). **Vision (screenshots) is verify-only** — confirm naturo's action was correct / dev-test
   reference — never the operating mechanism.
2. **Log every window here, completely**: when validated, framework, what `naturo see` returned,
   what `naturo click`/operation did, status, and — if unsolved — why/when/effect/blocker. A new
   agent continues this log or fixes previously-unsolved entries.

Columns: **see** = does `naturo see` expose the real content? · **operate** = can naturo act on it?
· **det.** = deterministic (a11y/CDP tree, repeatable) vs coord (vision-located coordinates).

| # | Window | Framework | Date | see | operate | det.? | Status |
|---|--------|-----------|------|-----|---------|-------|--------|
| 1 | 电脑管家 新功能提示 (promo popup, hwnd 1051478) | Qt 5.15 | 2026-07-31 | ❌ empty | ✅ dismissed | coord | operable-by-coord, NOT see-able |
| 2 | 电脑管家 软件市场 QMUI (hwnd 1378572) | Qt 5.15 | 2026-07-31 | ⚠️ nav only | ✅ nav by ref; content by coord | mixed | chrome see-able; content not |
| 3 | 电脑管家 AI欢迎窗 QQPCDownload (hwnd 3803148) | TXMiniSkin (Tencent DirectUI) | 2026-07-31 | ❌ empty (OCR partial) | ✅ minimized | coord | operable-by-coord, NOT see-able |
| 4 | 7-Zip 26.02 Setup wizard | Win32 standard | 2026-07-31 | ✅ full | ✅ Install/Close via UIA-Invoke | det | fully see-able + operable |
| 5 | 7-Zip File Manager (7zFM, hwnd 2493192) | Win32/UIA | 2026-07-31 | ✅ 111 nodes | ✅ read archive list | det | fully see-able |
| 6 | Windows Notepad (hwnd 7932338) | WinUI/UIA | 2026-07-31 | ✅ 45 nodes | ✅ new-tab via UIA-Invoke | det | fully see-able + operable |
| 7 | Chrome + web page (CDP, hwnd 657248) | Chromium/CDP | 2026-07-31 | ✅ 216 (UIA+CDP) | ✅ click via CDP, read_web_text | det | fully see-able + operable |
| 8 | WPS Office main window (OpusApp, hwnd 920682) | OpusApp (Word-compat) + CEF | 2026-07-31 | ⚠️ native yes / CEF no | ✅ native by ref; CEF by coord | mixed | see-able for native UI; CEF parts not |
| 9 | **WPS 表格 spreadsheet grid** (EXCEL7 child) | Excel-compatible OM | 2026-07-31 | ✅ **all cells** | ✅ **read + write** by ref (COM) | **det (COM)** | **SUPPORTED** — read `7dd71f8a`, write (S2) `d5b99e54` |
| 10 | **WPS 文字 / file COM** (`.docx` / `.xlsx` by path) | Word/Excel-compat COM servers | 2026-07-31 | ✅ full text / cells | ✅ **read + write + save** | **det (COM)** | **SUPPORTED** — `word_*` as-is; `excel_*` fixed `c9d070b4` |
| 11 | 钉钉安装 DingTalk installer (`*-Release.*.exe`) | custom GPU-composited | 2026-07-31 | ❌ no a11y / ✅ capturable after fix | ⚠️ coord (vision-located) | — | a11y-blind but now **capturable**; found+fixed a naturo capture defect (`af3fe63f`) |
| 12 | PotPlayer (免登录, hwnd 4328738) | Win32 custom skin | 2026-08-01 | ⚠️ frame+playlist yes / controls no | ⚠️ playlist List by ref; transport coord | partial | installed via 电脑管家 (naturo-driven); UIA exposes window + playlist List + search Edit; skinned transport controls have no a11y |
| 13 | VLC media player 3.0.23 (免登录, hwnd 1707074) | Qt (QAccessible) | 2026-08-01 | ✅ full menu + controls | ✅ menus/sliders/transport by ref | det (UIA) | **SUPPORTED** — full menu bar (媒体/播放/…/帮助), seek+volume Sliders, transport Buttons all UIA by ref; first-run privacy dialog also see-able (Button 继续) |
| 14 | WinRAR 7.23 (免登录, hwnd 724354) | Win32/UIA | 2026-08-01 | ✅ menus/toolbar/list (`--depth`) | ✅ by ref | det (UIA) | **SUPPORTED** — `see --depth 2` instant: MenuBar 应用程序, toolbar Pane, file List, StatusBar. ⚠️ **naturo perf finding**: default unlimited `see` took ~200s walking the huge D:-drive file List — see "Open items" (node-count safety backstop) |
| 15 | Visual Studio Code 1.131 (免登录, hwnd 10291472) | Electron (Chromium→UIA) | 2026-08-01 | ✅ menu + structure (`--depth`) | ✅ menus by ref | det (UIA) | **SUPPORTED** — Electron; `see --depth 4` exposes Web-content Document + MenuBar (File/Edit/Selection/View/Go/Run) by ref. Deeper (sidebar/editor/terminal) via more depth or CDP. Same big-tree perf caveat as #14. Inno installer driven by naturo (license radio + wizard). |
| 16 | Everything 1.4.1 (免登录, hwnd 855506) | Win32/UIA | 2026-08-01 | ✅ menu/toolbar/list (`--depth 2`) | ✅ by ref | det (UIA) | **SUPPORTED** — `see --depth 2` instant: MenuBar 应用程序, toolbar Pane, results List, StatusBar. ⚠️ **2nd hit** of the huge-list hang: `--depth 3+` descends the 1.18M-item List → times out (reinforces the node-count backstop in Open items). Installed via naturo driver (OK→我接受→下一步→安装→完成). Bandizip skipped — its custom (CEF-like) installer card didn't take synthetic clicks. |
| 17 | 福昕阅读器 (Foxit PDF Reader) 13.4 (免登录, hwnd 1445202) | Win32 ribbon/UIA | 2026-08-01 | ✅ full ribbon | ✅ toolbar by ref | det (UIA) | **SUPPORTED** — UIA exposes 功能区 ribbon, File Tab, Quick Access Toolbar (打开/保存/打印/撤销/重做…) all by ref. SOUI custom installer driven by naturo coord (agreement checkbox + 快速安装 — SOUI native takes synthetic clicks, unlike Bandizip's CEF). |
| 18 | MPC-HC 1.9.15 (免登录, hwnd 18745856) | Win32/UIA | 2026-08-01 | ✅ menu + transport | ✅ transport RadioButtons/Slider by ref | det (UIA) | **SUPPORTED** — transport ToolBar (播放/暂停/停止 RadioButtons + seek Slider) by ref; first-run default-player dialog also see-able (Button 是/否). Inno installer driven by naturo (language→我接受→下一步×5→安装→完成). Note: mis-mapped market columns once (col2≈x998 vs col3≈x1298) → accidentally started Malwarebytes WFC, cancelled. |
| 19 | Typora 1.12.4 (免登录, hwnd 69772) | Electron (Chromium→UIA) | 2026-08-01 | ✅ Document + text | ✅ readable/by ref | det (UIA) | **SUPPORTED** — Electron Markdown editor; UIA exposes the Welcome Document with all text ("感谢您使用 Typora…", feature list) + images by ref. Inno installer driven by naturo (Install-for-all → Next×2 → Install → Finish). (Snipaste skipped — tray-only, install didn't stick; Bandizip skipped — CEF installer.) |
| 20 | 格式工厂 (Format Factory) X64 5.16 (免登录, hwnd 11668280) | Win32 custom skin | 2026-08-01 | ✅ menu + panes/tabs | ✅ menu by ref | det (UIA) | **SUPPORTED** — Menu Bar (任务/皮肤/语言/选项/帮助) + 视频 pane w/ format-category Tab by ref; update-check dialog fully see-able (下载 Button, ProgressBar, CheckBox). qqpc installer clean (no PUP); unchecked shortcut boxes + 一键安装 via naturo coord. |
| 21 | Firefox 标准版 (免登录, hwnd 2100526) | Gecko (UIA/IA2) | 2026-08-01 | ✅ chrome (`--uia --depth 8`) | ✅ tabs/address bar by ref | det (UIA) | **SUPPORTED (chrome)** — `--uia --depth 8`: 浏览器标签页 tabs, 打开新标签页, address bar ComboBox (e78) by ref. ⚠️ **findings**: page-content Document is offscreen/empty (Firefox **lazy a11y** — not activated until an AT is detected); **`--ia2` returns empty** (naturo IA2 gap on Firefox / lazy a11y). To read page content, a11y must be force-activated. |
| 22 | BitComet 2.18 (免登录, hwnd 2559864) | Win32/UIA | 2026-08-01 | ✅ full toolbar | ✅ by ref | det (UIA) | **SUPPORTED** — full toolbar (添加存档/Search/开始/停止/预览/目录/属性/删除/选项/退出) + 登录/注册 all by ref; login OPTIONAL (basic BT download 免登录, login only for faster speed). NSIS installer driven by naturo (OK→下一步→我接受×2→安装→完成). |
| 23 | IrfanView 4.62 (免登录, hwnd 397930) | Win32/UIA | 2026-08-01 | ✅ full toolbar | ✅ by ref | det (UIA) | **SUPPORTED** — classic Win32; ToolBar Open/Slideshow/Save as/Print/Delete/Cut/Copy/Paste/Undo all named by ref. Installer driven by naturo (added "下一页(N)" to the driver's advance keywords). |
| 24 | SumatraPDF 3.3.3 (免登录, hwnd 790664) | Win32 custom-drawn | 2026-08-01 | ⚠️ tabs/page-nav yes / icons no | ⚠️ page Edit + tabs by ref; icon buttons coord | partial | tabs (Tab e4), page-number Edit (e11) + toolbar structure see-able; owner-drawn icon toolbar buttons unnamed, PDF content not a11y-text (like PotPlayer). Installer driven by naturo (安装 button). |
| 25 | PicPick (免登录, hwnd 1577086) | Win32 ribbon/UIA | 2026-08-01 | ✅ ribbon backstage | ✅ by ref | det (UIA) | **SUPPORTED** — ribbon image editor; Backstage view + 主页 pane + Back button by ref via UIA; first-run default dialog (是/否) also see-able. Installed silently via 电脑管家. (有道翻译 skipped — custom installer's agreement radios don't take synthetic clicks, like Bandizip.) |
| 26 | Audacity 2.4.2 (免登录, hwnd 3018654) | wxWidgets/UIA | 2026-08-01 | ✅ full menu + track view | ✅ menus by ref | det (UIA) | **SUPPORTED** — wxWidgets audio editor; UIA exposes the whole shell: 11-item MenuBar (文件/编辑/选择/视图/播录/轨道/生成/效果/分析/工具/帮助) all actionable by ref, Top Panel transport toolbars, 轨道视图 Table, StatusBar (version + 已停止). First-run 欢迎 dialog dismissed by ref (确定). Inno installer driven end-to-end by naturo: TSelectLanguageForm 确定 by ref → wizard 下一步×4 → 安装 → 完成. **naturo finding**: the Inno owner window is a 0×0 `TApplication`; the real UI is a separate `TSelectLanguageForm`/`TWizardForm` top-level — the driver's EnumWindows title-substring resolution handles this correctly (don't target the owner). |
| 27 | WinMerge 2.16 (免登录, hwnd 12847882) | MFC/Win32 UIA | 2026-08-01 | ✅ full menu + toolbar/status | ✅ menus by ref | det (UIA) | **SUPPORTED** — MFC diff/merge tool; UIA exposes 7-item MenuBar (文件/编辑/视图/工具/插件/窗口/帮助) all by ref, ToolBar Pane, 工作区 Pane, multi-field StatusBar (NUM etc.). Installed **silently** by 电脑管家 (no wizard window at all) → launched via `naturo app launch --path`, evaluated, then `naturo app quit`. (Notepad++ NOT in the 电脑管家 store — search returns Microsoft XML Notepad + other editors; skipped rather than install a wrong-app substitute.) |
| 28 | HandBrake 1.0.7 (免登录, hwnd 5115630) | WPF/.NET (HwndWrapper) UIA | 2026-08-01 | ✅ menu + named toolbar + labeled controls | ✅ toolbar buttons & combos by ref | det (UIA) | **SUPPORTED** — WPF video transcoder; UIA fully exposes it: Menu (File/Tools/Presets/Queue/Help), ToolBar with **named** Buttons (Choose Source/Start Encode/Add to Queue/Show Queue/Preview Encode/Activity Window), Source panel with labeled ComboBoxes (Title/Angle/chapter-range) + Edit fields + spinner Buttons — all by ref. Confirms naturo's **WPF path** with deep control coverage. NSIS installer driven by naturo (Next→I Agree→Install→Finish). |
| 29 | CMake (cmake-gui) 3.15.5 (免登录, hwnd 3543146) | Qt 5 (a11y-less build) | 2026-08-01 | ⚠️ tree empty; ✅ OCR recovers UI | ⚠️ coord via OCR text | OCR (structure det-empty) | **PARTIAL — naturo finding: build-dependent Qt a11y.** Unlike VLC/PotPlayer/Format Factory (Qt builds that expose full UIA trees), this cmake-gui Qt5 build exposes **only the top window/TitleBar** to *both* `--uia --depth 10` (7 chrome nodes) *and* `--msaa` (1 bare Client) — the widget tree is absent. **`--ocr` fully recovers it**: File/Tools/Options/Help menu, "Where is the source code" + Browse Source, "Where to build the binaries" + Browse Build, Search — so naturo still operates it via OCR-text + coords. Parallel to the Firefox lazy-a11y gap (#21): the moat's OCR fallback is what keeps such windows drivable. **MSI installer FIX validated here** → see Open items (driver now follows the wizard by PID across per-page title changes). |
| 30 | CrystalDiskInfo 9.7.2 x64 (免登录, hwnd 1446076) | Win32 dialog (#32770) UIA | 2026-08-01 | ✅ disk buttons + full S.M.A.R.T. data List | ✅ disk-select buttons by ref | det (UIA) | **SUPPORTED — hits the "extract real valuable data" gate.** UIA exposes per-drive selector Buttons (health+temp e.g. "良好 28°C C: D:"), the health-% and temperature Buttons, and the **full S.M.A.R.T. attribute List with real data** — Header (ID/属性名称/当前值/最差值/临界值/原始值) + ListItems ("01 严重警告标志 00000000000000", "02 综合温度"…). naturo reads genuine disk-health telemetry, not just chrome. Inno installer driven by naturo (language OK → accept → Next×4 → Install → Finish) via the **PID-follow** driver (handled the "Select Setup Language"→"Setup - CrystalDiskInfo 9.7.2" title change). |
| 31 | CPU-Z 2.20.2 (免登录, hwnd 7211030) | Win32 dialog (#32770) UIA | 2026-08-01 | ✅ full live CPU telemetry as text | ✅ Tab + 确定 by ref | det (UIA) | **SUPPORTED — extract-real-valuable-data gate.** UIA reads the complete CPU readout as Text nodes: "Intel Core i7 12700F"/"Alder Lake", 规格 "12th Gen Intel(R) Core(TM) i7-12700F", 插槽 Socket 1700 LGA, 核心速度 4489.02 MHz, 倍频 x45.0, 总线速度 99.76 MHz, TDP 65.0 W, 工艺 10纳米, voltage 1.166 V, L1/L2/L3 cache, family/model/stepping — all by ref, plus the Tab control (CPU/Caches/Mainboard/Memory/…) and 确定. Inno installer driven by naturo (accept→Next×4→Install→Finish); Finish opened cpuz_readme in Notepad++ (present on this host) → closed by naturo. |
| 32 | DB Browser for SQLite 3.8.0 (免登录) | Qt5 (stale 2015 build) | 2026-08-01 | ❌ no window — process exits immediately | n/a | n/a | **VALIDATION FAILURE (app quality, not naturo) — installed OK, crashes on launch.** NSIS install via naturo succeeded (`C:\Program Files\SqliteBrowser3\bin\sqlitebrowser.exe`, dated 2015-12-26 = v3.8.0), but the exe **exits immediately** on Win11 (dead Qt5.4/icu54 build). Not evaluable. **naturo fix shipped from this**: `app launch --wait-until-ready` reported the crash as a bare "Application not found", indistinguishable from a truly-missing app (QA-Mariana had flagged this as misleading). Fixed `cli/_app/lifecycle.py` to append the error's `suggested_action` in text mode → now "Application not found: …sqlitebrowser.exe **(Process exited immediately after launch)**" vs "**(File does not exist)**". 85 launch/CLI tests green. |
| 33 | ScreenToGif 2.34.1 (免登录, hwnd 4198550) | WPF/.NET (HwndWrapper) | 2026-08-01 | ✅ structure + 4 mode buttons clickable; OCR labels them | ✅ buttons by ref, labels via OCR | UIA(structure)+OCR(labels) | **SUPPORTED — clean cascade-fusion (moat) example.** WPF launcher exposes TitleBar, "新版本可用" hyperlink, and the 4 primary mode Buttons (e12–e15) **clickable by ref** — but they carry **no AutomationProperties.Name** (WPF icon cards), so the tree can't say which is which. `--ocr` supplies the labels (录像机/摄像头/画板/编辑器 + 选项), fused onto the UIA buttons → fully operable. Exactly the UIA-structure + OCR-labels fusion the moat is built on. Custom **WinForms installer** driven by naturo coords+capture (unchecked FFmpeg 24.6MB to skip a slow download; 我接受→下一步→安装→完成); .NET 4.8 already present. Minor: `naturo app quit --app ScreenToGif` graceful path hung (>120s) → force-kill; worth a look but not blocking. |
| 34 | Greenshot 1.2.10 (免登录) | .NET WinForms (tray-first) | 2026-08-01 | ⚠️ dialogs see-able; main editor tray-invoked only | ✅ dialog buttons by ref | det (UIA) on dialogs | **PARTIAL — tray-first app.** Inno install driven by naturo (the driver gained a real capability here: the Chinese-localized `TSelectLanguageForm` title is "选择安装语言" — no "Setup" substring — so I drove with "安装", which matches both it and "安装 - Greenshot"; PID-follow then carried 确定→accept→下一步×6→安装→完成). Greenshot runs **in the tray**; its editor only appears on an interactive capture, which isn't triggerable headlessly (`/openfile <png>` just forwarded to the tray instance without opening a window). naturo **cleanly read the WinForms hotkey-conflict Warning dialog** it raised (full body text about "Alt + PrintScreen" + 中止/重试/忽略 Buttons all by ref → dismissed via 忽略 e4), confirming its WinForms UI is fully see-able — but no persistent main window was reachable in this flow, so it doesn't clear the "reach main window + extract data" gate. Comparable to Snipaste (#tray-only skip) but with WinForms UI confirmed. |
| 35 | HWiNFO64 v5.54 (免登录) | Win32 (#32770) — kernel-driver-gated | 2026-08-01 | ⚠️ dialogs see-able; main summary unreachable (driver blocked) | ✅ dialog buttons by ref | det (UIA) on dialogs | **PARTIAL — environment driver-gating (not naturo, not app quality).** Inno install driven by naturo (Next×3→Install→Finish). On launch HWiNFO needs to install its **kernel sensor driver**; that's blocked here ("Cannot install the HWiNFO driver! Check user rights and possible antivirus filters" — 电脑管家 self-protection / session context), so the process **exits** and no System-Summary/Sensors window ever appears. naturo **cleanly read every dialog it did show**: the startup Welcome (Run/Settings Buttons + Sensors-only/Summary-only CheckBoxes + version text, all by ref) and the Error dialog (full body text + 确定 by ref, dismissed). Contrast #30/#31 (CrystalDiskInfo/CPU-Z) which read HW data fine without a driver install — HWiNFO specifically requires a ring-0 driver. Doesn't clear the main-window/extract-data gate in this env. |
| 36 | Notepad++ (免登录, hwnd 594604) | Scintilla + Win32/UIA | 2026-08-01 | ✅ full menu + tabs + StatusBar + **Scintilla document** | ✅ menus/tabs by ref | det (UIA + scintilla) | **SUPPORTED — shows naturo's dedicated Scintilla source.** 13-item MenuBar (文件/编辑/搜索/视图/编码/语言/设置/工具/宏/运行/插件/窗口/?) all by ref, Tab + TabItem by ref, ToolBar, StatusBar with live data (Normal text file, length/lines, Ln/Col/Pos, Windows CR-LF, UTF-8, INS), and crucially `[Document] "Scintilla editor" [scintilla]` — naturo has a **dedicated Scintilla recognizer** exposing the editor content ("writable again"), a moat capability (Scintilla underlies many editors). **Note on provenance:** Notepad++ is **not in the 电脑管家 store** (see #27) and was already present on this host; evaluated here because the market's second-stage installer downloads stalled this stretch (see Open items) — logged transparently. User's unsaved file was open, so left running (no teardown). |
| 37 | Windows 计算器 (Calculator, UWP, hwnd 267736) | UWP/WinUI XAML (ApplicationFrameWindow→CoreWindow) | 2026-08-01 | ✅ full pad + display by ref; ✅ operable (keyboard) | ✅ digits/display by ref; ⚠️ operator-button *click* no-op | det (UIA) | **SUPPORTED — fills the flagged `calc` TODO; confirms naturo UWP/WinUI coverage.** `--depth 8` exposes the whole XAML tree: display "显示为 N", all digit Buttons (零…九), all operator Buttons (加/减/乘以/除以/等于/百分比/平方/平方根/倒数/清除…), memory + nav, all by ref. **End-to-end operation verified**: `naturo type "7+8"` + `press enter` → display "显示为 15". ⚠️ **naturo finding (minor, for follow-up):** clicking the **operator** buttons by ref-Invoke *and* by --coords was a **no-op on the maximized instance** (digit-button clicks landed fine → repeated "78"), while **keyboard input works perfectly** — an asymmetric click quirk on UWP operator buttons worth a look; not blocking (keyboard path fully functional). Already-present system app (not market-installed); evaluated during the market-download stall. |
| 38 | Windows 任务管理器 (Task Manager, hwnd 529848) | Win11 WinUI XAML (DesktopWindowXamlSource) | 2026-08-01 | ✅ toolbar + **live system telemetry** + process DataGrid | ✅ toolbar/search by ref | det (UIA) | **SUPPORTED — strong extract-real-valuable-data.** `--depth 5` UIA exposes: toolbar Buttons (运行新任务/结束任务/效率模式/增加应用栏) + 搜索框 Edit by ref, and the process view's **live aggregate metrics read straight from the column HeaderItems** — CPU **13%**, 内存 **92%**, 磁盘 **1%**, 网络 **1%** (as Edit nodes by ref) — plus the "进程" DataGrid with H/V scrollbars and the 应用/后台进程 groups. Individual process rows live in a **virtualized XAML DataGrid** (readable via targeted expansion; a plain deep walk crosses the XAML-island boundary and falls back to MSAA — minor traversal note). Already-present system app (not market-installed); evaluated during the market-download stall. |
| 39 | Windows 注册表编辑器 (regedit, hwnd 529934) | Win32 TreeView + ListView (RegEdit_RegEdit) | 2026-08-01 | ✅ hive Tree + value List with **real data** | ✅ tree/list by ref | det (UIA) | **SUPPORTED — extract-real-valuable-data + navigable structure.** Two classic Win32 common controls both fully exposed: the **Tree** with all 5 root hives (HKEY_CLASSES_ROOT/CURRENT_USER/LOCAL_MACHINE/USERS/CURRENT_CONFIG) as TreeItems by ref under 计算机, and the value **List** with Header (名称/类型/数据) + ListItems carrying **genuine registry data** by ref — e.g. FindFlags REG_DWORD 0x00000000, LastKey REG_SZ "计算机\HKEY_CURRENT_USER\…\Regedit", View REG_BINARY with the full byte blob. Address-bar Edit + MenuBar also by ref. Read-only (no keys modified). Already-present system app; evaluated during the market-download stall. |

---

## Details

### 1. 电脑管家「新功能提示」promo popup — hwnd 1051478 (QQPCTray.exe)
- **Framework:** Qt 5.15 (window class `Qt51514QWindowIcon`), WS_EX_LAYERED|TOPMOST, 0 child HWNDs, elevated.
- **see:** `naturo see` → **1 node, empty Pane** (`e1 Pane "腾讯电脑管家"`). No content. Qt widgets custom-painted, no `QAccessible`.
- **operate:** multi-page onboarding (广告拦截 → AI助手). Dismissed by clicking「暂不开启」via `naturo click --coords` (client-relative, auto-fallback PostMessage after elevation). Both pages advanced/closed. ✅
- **Status:** operable-by-coordinate only; **NOT see-able**.
- **Blocker to deterministic see:** Qt has no a11y here; the deterministic fix (inject a Qt introspector) is **blocked — 电脑管家 self-protection** strips `PROCESS_CREATE_THREAD` from handles to its processes (`CreateRemoteThread` → err 5). Legitimate security-suite defense; we do not bypass it.

### 2. 电脑管家 软件市场 QMUI — hwnd 1378572 (Qt64/QMUI.exe, pid 99728)
- **Framework:** Qt 5.15, elevated. (10 QMUI.exe processes, one per module/window.)
- **see:** early in session returned empty/frame-only (degraded session / a11y not activated); **later `naturo see` returned 71 deterministic UIA nodes** exposing the **chrome**: nav (`首页 e48 / 分类 e50 / 更新 e52 / 卸载 e55`), left rail (电脑+/安全AI/AI专区/下软件/玩游戏), search `Edit e57`. **The app-grid content (app tiles, 安装/一键安装 buttons) is NOT in the tree** (`match "WPS 安装"` → 0).
- **operate:** nav is clickable **by ref** — verified `naturo click e50` (分类) navigated to the Categories page (vision-confirmed). Content (install buttons) has no ref → only reachable by `naturo click --coords`.
- **Status:** chrome **see-able + operable by ref**; content **not see-able** (coord-only), can't be made see-able (self-protection blocks injection).

### 3. 电脑管家「AI电脑管家」欢迎窗 — hwnd 3803148 (QQPCDownload_home_310056.exe)
- **Framework:** **TXMiniSkin** (Tencent's own DirectUI skin), WS_EX_LAYERED, 0 child HWNDs, elevated. Different framework from the Qt main UI.
- **see:** `naturo see` → **1 empty Pane**. `naturo see --ocr` → **3 uncertain OCR text nodes** (标题栏「腾讯电脑管家」/「AI电脑管家」/副标题) with estimated bounds; **missed the「立即体验」button and window controls**.
- **operate:** minimized via `naturo click --coords` on the minimize button (auto-fallback PostMessage). Verified `IsWindow=True, IsIconic=True` (reversible). ✅
- **Status:** operable-by-coordinate; **NOT see-able** (OCR partial/uncertain, no buttons).

### 4. 7-Zip 26.02 (x64) Setup wizard — standard installer (launched by 电脑管家)
- **Framework:** standard Win32 dialog (has full UIA).
- **see:** `naturo see --window Setup --match install` → `e5 Button "Install"`; later `e7 Button "Close"`. Fully see-able.
- **operate:** `naturo click e5 --method uia` (Install, kept default dir `C:\Program Files\7-Zip\`), then `e7` (Close). Installed successfully. ✅
- **Status:** **fully see-able + operable, deterministic.** This is the "auto-handle install dialog" case working the right way (by ref).

### 5. 7-Zip File Manager (7zFM.exe) — hwnd 2493192
- **Framework:** Win32/UIA.
- **see:** `naturo see` → **111 deterministic UIA nodes**: archive file list (name/size/compressed/date/CRC/algo), toolbar (添加/解压/…), menus. Matched `7z l` CLI exactly.
- **operate:** read valuable data (the archive contents) — G2 satisfied deterministically.
- **Status:** **fully see-able**, deterministic.

### 6. Windows Notepad — hwnd 7932338
- **Framework:** Win11 Notepad (WinUI/XAML, UIA).
- **see:** `naturo see` → **45 UIA nodes** (tabs, formatting buttons, menus, document text). Fully see-able.
- **operate:** `QAccessible/UIA InvokePattern` on「添加新标签页」created a new tab (verified via `see`: 2 TabItems) — worked **even in the dead-input console** because UIA-Invoke bypasses the OS input stack. Typing via PostMessage went to the wrong focus during the dead-input phase (a foreground/focus issue, not a see issue).
- **Status:** **fully see-able + operable** (UIA-Invoke).

### 7. Chrome + web page (CDP) — hwnd 657248 (launch_browser)
- **Framework:** Chromium; naturo attaches via CDP (remote-debugging port).
- **see:** `naturo see` → **216 nodes** (UIA 38 chrome + **CDP 178 DOM**), deterministic, token-lean. `read_web_text` returned the rendered 百度热搜 ranking (valuable data).
- **operate:** `naturo click e50 --method cdp` dispatched via the debug protocol (bypasses input stack). 
- **Status:** **fully see-able + operable** via CDP. This is naturo's clean path for all Chromium/web content.

### 11. 钉钉 (DingTalk) installer — 「钉钉安装」window (App#3, install step)
- **Install channel (naturo-driven):** used naturo's **CDP browser** to open `dingtalk.com/download`,
  extracted the Windows client link deterministically (`browser eval`), and downloaded the official
  bootstrapper `dingtalk_downloader.exe` (2.8 MB). Ran it via `naturo app launch`; it fetched the full
  472 MB installer `8.3.45-Release.260720005.exe` and opened the 「钉钉安装」window. **This part worked
  cleanly** (no winget, no coord).
- **Installer window — a11y-blind, and it exposed a real naturo capture bug (now fixed):**
  1. **Not see-able (a11y):** `see` → a single bare `[Client] [msaa]` node, no buttons/text
     (custom GPU-composited UI, no UIA/MSAA content — like 电脑管家's DirectUI). This part is inherent.
  2. **Capture was blanking it — root-caused + fixed.** User observed the window had text+buttons, then
     went **blank white** "after naturo ran / after a screenshot." Isolation experiment (fresh window,
     passive `capture --screen` BitBlt only → renders fine; then `capture --hwnd` PrintWindow → window
     goes white on screen): **`capture --hwnd` (PrintWindow / `WM_PRINT`) is destructive on
     GPU-composited windows** — the returned bitmap is blank AND the live window stops presenting. `see`
     hits the same path (it captures internally for its snapshot/vision step). The blank is **recoverable**
     (minimize/restore forces a re-present). **Fixed `af3fe63f`:** `capture_window` detects the blank
     frame, heals the window, and re-captures non-destructively via screen BitBlt cropped to the window
     rect. Verified live: `capture --hwnd` now returns the true content (logo / 立即安装 / 我已阅读并同意 /
     自定义安装) and leaves the window intact. So the installer **is capturable now** — vision (verify-only)
     can locate its buttons for a coord-click.
  3. **Behind the foreground + no silent flag:** the window sat below the terminal in z-order (a blind
     `click --coords` hit the terminal, hwnd 199508), and `--args /S` (NSIS silent) is ignored.
- **Status:** installer is **a11y-blind but capturable**; install is reachable by vision-located
  coord-click (foreground it first) — the sanctioned fallback. Bigger win: **found+fixed the naturo
  capture defect (`af3fe63f`)** that blanks all GPU/Electron windows. **The real target is the DingTalk
  *app*** (Electron → CDP DOM read, the moat test) + **QR login (needs the user)** — both come after
  install.

### 10. WPS 文字 (Writer) + file-based Office COM — `.docx` / `.xlsx` by path
- **Framework:** WPS registers the standard Office COM ProgIDs as compat servers —
  `Word.Application` (→ WPS 文字, `Name == "Microsoft Word"`) and `Excel.Application` (→ WPS 表格,
  `Name == "Microsoft Excel"`, Version 16.0). The WPS-native ProgIDs (`KWPS.Application`,
  `KET.Application`) fail to Dispatch (invalid class string / bitness), but the compat ones work, so
  naturo's file-based COM tools drive WPS unchanged.
- **see/operate (Word):** `word_read(path)` / `word_write(path, text)` (dedicated
  `DispatchEx("Word.Application")` instance). Verified: wrote `wps_test.docx` (季度销售报告 …, 69
  chars) and read the identical text back. `word_write` on a new path does `Documents.Add` + `SaveAs`
  (= "new document"); `append=True` supported. Covers S3/S4/S5/S6 for documents. No fix needed.
- **see/operate (Excel by path):** `excel_read` / `excel_write` (`DispatchEx("Excel.Application")`).
  Needed a **naturo fix**: `excel_write` read `ws.Name` **after** `wb.Close()`, and WPS releases the
  worksheet proxy on close → OLE `0x800a01a8`; MS Excel tolerated the stale read, masking the bug.
  Fixed `c9d070b4` (capture the sheet name before closing). Verified: `excel_write` A1/B1 →
  `excel_read` round-trip on a fresh file, then removed the temp file.
- **Status:** **SUPPORTED — read + write + save, deterministic (COM), easy (path only).** This is the
  file-path counterpart to the live-window grid (#9): use #9 (`see` / `set <ref>`) when a
  workbook is already open and you don't know the path; use these when you have the file path.

### 9. WPS 表格 spreadsheet grid — EXCEL7 child under the OpusApp window
- **Framework:** Excel-compatible object model. WPS mirrors Excel's window hierarchy (an `EXCEL7`
  grid nested under the top-level `OpusApp`) and exposes the standard Excel OM on that grid window
  (`Application.Name == "Microsoft Excel"`), even though its `Application` registers in neither the
  ROT nor the `Excel.Application` class moniker (different ProgID + bitness).
- **see (read):** `naturo see` → **every non-empty cell** as a deterministic `com` DataItem
  with value + screen coords + ref (e.g. `e260 [com]` = A1). Requires **no** extra flags. Fixed in
  `7dd71f8a` (`is_excel_window` matches an EXCEL7-containing window; `AccessibleObjectFromWindow(
  OBJID_NATIVEOM)` binds the Window OM cross-bitness). Verified vs the known test sheet.
- **operate (write):** `naturo set <ref> <value>` on a `com_*` cell routes to `write_excel_cell`
  (`ActiveSheet.Range(addr).Value = …`) — **deterministic, GUI/z-order-independent** (no coordinate
  click, works with WPS in the background). Verified live: A1 `999`→`产品`, A2 `苹果`→`红苹果`,
  B2 `10`→`12` (numeric), each round-tripped through `naturo see`. Numeric strings coerce to number;
  leading-zero strings stay text. Fixed in `d5b99e54` (S2). The old coord-click path was rejected
  (imprecise + hijacked by the foreground terminal).
- **Status:** **SUPPORTED — read + write, deterministic (COM), easy (ref only, no aux params).**

### 8. WPS Office 12.1.0.28043 — main window hwnd 920682 (D:\...\Kingsoft\WPSOffice\...\wps.exe)
- **Install:** via 电脑管家 software market, **driven by naturo** — `naturo click --coords` on the WPS「安装」tile (coord found by vision, action via naturo). 电脑管家 downloaded+installed silently; completion detected by the WPS processes/window appearing (the right naturo-native signal is `wait_for_window`, **not** reading 电脑管家's custom-painted "39%" progress, which isn't in any see tree).
- **Framework:** main window class **`OpusApp`** (WPS deliberately reuses MS Word's class for compat) — **NOT Qt.** So the Qt-injection moat does **not** apply to WPS. Mixed UI: native `OpusApp` chrome + embedded **CEF** web views (`KxCefWebViewPrivateBrowser`) for the login dialog and start page.
- **see:** `naturo see` → **54 UIA nodes** for the native shell (新建 button, tabs, documents). **CEF content is NOT exposed** (login form / start-page 演示·表格·文字·PDF tiles → `match` = 0). WPS's CEF has **no CDP debug port** (no `--remote-debugging-port`, no listening port) → can't attach CDP either.
- **operate:** the **native** WPS confirm dialog「未登录仅支持部分功能」→「暂不登录」was in the tree (`e12 Button`) and **clicked by ref** ✅ (proper see→click). The **CEF** login form's × had no ref → closed via `naturo click --coords` (fallback). So: **native UI = see-able + click-by-ref; CEF UI = coord-only.**
- **Status:** installed + login-skipped, WPS usable. Native shell adaptable via naturo UIA see→click. **Document/sheet content** (the real valuable data) best via **WPS COM automation** (WPS/KWPS/Ket.Application, like naturo's Excel/Word COM) — deterministic, GUI-independent — TODO. CEF surfaces need coords (no CDP).
- **Moat note:** WPS is **not** a valid target to validate the *Qt* injection introspector (it isn't Qt). Use an actual Qt app (Navicat / 为知 / 富途) for that.

---

## 免登录 sweep progress (goal: 50 apps via 电脑管家 + naturo evaluate/fix)

**Installed + evaluated this run: 25 apps (#12–31, #33, #36–39; #34 Greenshot &
#35 HWiNFO64 PARTIAL; +#32 DB Browser installed but its stale 2015 build crashes
on launch — a failure).** #36–39 (Notepad++, Calculator, Task Manager, Registry Editor)
were evaluated from already-present installs during a 电脑管家 download stall (see Open items). Wide tech coverage, mostly
SUPPORTED via UIA: Qt (VLC), Win32/MFC (WinRAR/Everything/MPC-HC/IrfanView/
BitComet/WinMerge), Electron (VS Code/Typora), WPF/.NET (HandBrake), Win32-ribbon
(Foxit/PicPick), wxWidgets (Audacity), custom-skin (PotPlayer/Format Factory/
SumatraPDF — partial), Gecko/UIA (Firefox chrome), a11y-less Qt (cmake-gui —
OCR fallback). Real naturo
findings: capture fix enables driving the **elevated** 电脑管家 market by
vision-located coords; node-count `see` backstop (huge lists); Firefox lazy-a11y /
`--ia2` gap.

**Installer-resistance pattern (finding).** ~40% of the harder apps have installers
that resist generic naturo automation and were **skipped**:
- **Custom agreement-gated cards** (synthetic clicks don't fire / a required
  agreement checkbox stays unchecked, disabling the install button): Bandizip &
  HoneyView (Bandisoft CEF card), 有道翻译, QQ影音. 
- **MSI wizards** that pop an error/warning dialog or hang: Inkscape, KMPlayer.
  (CMake's MSI is **now handled** — see the driver fix below; #29 installed cleanly.)
- **Non-standard button text / finicky pages**: EditPlus, EmEditor (driver gained
  keyword + a position fallback; still app-specific).
- **Tray-only** (no main window to evaluate): Snipaste, Ditto.

Reliable path: standard NSIS/Inno/silent/**MSI** installers driven by
`tools/drive_installer.py` (naturo see→click by ref) + top-left search-result at a
fixed coord. The next agent continues from #30; prefer standard-installer apps and
verify the search's top result matches before clicking (columns are at screen
x≈700/998/1298). The 电脑管家 store carries mostly Chinese/OEM titles — some
Western apps (e.g. Notepad++) aren't present; don't substitute a same-keyword
different app. Market window client origin is screen (330,0): image px (ix,iy) →
screen (330+ix, iy); nav 下软件 ≈ screen (385,460), store search field ≈ (920,50),
clear-X ≈ (1007,50).

## Open items / for the next agent

- **⚠️ 电脑管家 second-stage download stall (environmental, intermittent).** The store
  downloads a small **stub** first (e.g. PuTTY listed as 228.9 KB "已完成" in 下载列表),
  then fetches the real installer at install time. During this stretch that second
  fetch stalled/near-zero-throughput for **DiskGenius (~80MB)** and **PuTTY**, so the
  installer window never appeared even though the queue showed 已完成 — nothing landed
  on disk. Earlier apps (#12–#35) downloaded fine, so it's transient network
  degradation, not a broken flow. The download flyout (右上 download icon → separate
  Qt popup hwnd, ~404×645 @ screen 986,58) lists items but clicking a completed item
  did not re-trigger install. Mitigations for the next agent: retry later; prefer
  small (<20MB) packages; if a big download blocks the queue, cancel it. #36 Notepad++
  was evaluated from an already-present install to keep making progress during the stall.
- **MSI installer driving — FIXED in `drive_installer.py` (this session, #29 CMake).**
  MSI wizards (`MsiDialogCloseClass`) change the *window title* per page
  ("CMake Setup" → "Install Options" → "Ready to Install" → "Installing"…), so the
  old title-substring resolution lost the window after the first page and reported
  "installer finished" while it was still on page 2 (also spawned duplicate wizards
  on retry). Fix: `find_installer_dialog(substr, pid)` resolves once by title, then
  **pins the PID and follows any wizard-class window of that PID** (largest = main
  page) across title changes, with a short retry so brief page-swaps don't read as
  gone. NSIS/Inno already worked (stable titles); this unblocks the whole MSI class.
  *Productization note:* this belongs in naturo proper as an `naturo install --wizard`
  / installer-driver helper (the logic is generic: foreground → see → click advance/
  accept by ref → follow-by-PID). Currently a support-tools script, not shipped.
- **naturo `see` node-count safety backstop (perf).** Default `see` is unlimited depth
  (`--depth 0`, by design #1289). On a file-manager-style window with a huge virtualized
  list (WinRAR showing the D: drive, #14) the native UIA walk took ~200s — reads as a
  hang. Workaround today: `--depth N`. Proper fix: a *pure safety backstop* on total node
  count in the native tree walk (allowed by #1289 — a very high cap that only prevents
  runaway traversal, not a functional clamp). Native `naturo_core.dll` change (MSVC present).
- **电脑管家 (App#1):** content (software grid, install/uninstall buttons) is not see-able and injection is self-protection-blocked → operations there are coordinate-based, which violates iron-law #1's spirit. Acceptable only as a fallback; a fully clean 电脑管家 adaptation is **not currently achievable** (its self-protection is legitimate; we don't bypass it).
- **Qt introspector (moat):** `C:\Users\Naturobot\.naturo-qt\{nq_probe.cpp, qt_introspect.ps1}` compiles and injects; **works on normal Qt apps** (no self-protection). To validate: run it against a plain Qt app (e.g. WPS if Qt) and feed the deterministic QWidget tree into `naturo see`. Injection is a user-run, security-gated step.
- **Windows Calculator (calc):** ✅ validated as #37 (UWP/WinUI SUPPORTED; 7+8=15 via
  keyboard). Left-open follow-up: operator-button *clicks* no-op on the maximized
  instance (see #37) — a small UWP click quirk to root-cause when convenient.
