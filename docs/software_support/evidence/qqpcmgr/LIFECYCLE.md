# App#1 腾讯电脑管家 — full install→use→uninstall lifecycle (VERIFIED)

Goal: adapt 电脑管家 (App#1) so naturo can use it to install other software, auto-handling any
install dialog, and cover the whole install→use→uninstall lifecycle — **in the headless console
session (no RDP, no working OS input stack).**

## Enabling technique (the breakthrough)
- 电脑管家 = **Qt 5.15 QtWidgets** (window class `Qt51514QWindowIcon`, 0 child HWNDs, empty UIA/MSAA
  tree) running **elevated**. Console session has **no functional synthetic input** (SendInput/
  SetCursorPos/naturo core all `System/COM error`).
- Fix: run the driver **elevated**, then **`PostMessage(hwnd, WM_MOUSEMOVE/WM_LBUTTONDOWN/WM_LBUTTONUP,
  MK_LBUTTON, MAKELPARAM(clientX,clientY))`** and **`WM_CHAR`** to the Qt top-level HWND. Qt's window
  proc dispatches the posted messages to the widget at those client coords — **no OS input stack, no
  injection; elevation defeats UIPI**. Targets located by vision (screenshot → client coords).
- Standard (non-Qt) dialogs (the app installers 电脑管家 launches) are driven by **naturo UIA Invoke**
  (works once elevated). See [[project_naturo_qt_postmessage_operate]].

## The run (test app: 7-Zip 26.02, chosen small/clean/login-free)
1. **INSTALL** — focused 电脑管家 软件市场 (QMUI hwnd), PostMessage-typed `7-zip` into the search box
   (WM_CHAR) + Enter → results. PostMessage-clicked 7-Zip **安装**. The **7-Zip 26.02 (x64) Setup**
   wizard appeared (`C:\Program Files\7-Zip\`, Install/Cancel). **naturo auto-decision: keep default
   folder, UIA-Invoke `Install`**, then UIA-Invoke `Close`. → `C:\Program Files\7-Zip\7zFM.exe` present,
   v26.02. (evidence 18–21.png)
2. **USE** — launched `7zFM.exe test_archive.zip`; naturo read its UIA tree (111 nodes, deterministic)
   → archive file list = **valuable data**: 18_softmarket_front.png (340,362 / CRC 664450CA),
   20_install_click.png (370,055 / 6B11EF72), FINDINGS.md (8,748 / A9732D85) — **matches `7z l` CLI
   exactly**. (evidence: see_ui_tree output)
3. **UNINSTALL** — back to 首页, PostMessage-clicked **卸载** tab → installed-software list (113).
   PostMessage-clicked 7-Zip's **卸载** → removed. List **113 → 112**, 7-Zip gone; **`C:\Program
   Files\7-Zip` deleted + registry uninstall key cleared**. (evidence 22–25.png)

## Gate status (G1–G7)
- G1 reach real value ✓ · G2 extract valuable data ✓ (deterministic UIA, matched CLI) · G3 operate ✓
  (install/use/uninstall) · G4 vision cross-check ✓ (screenshots + UIA vs CLI) · G7 versions ✓
  (电脑管家 18.2.30833.214, 7-Zip 26.02).
- **G5 token-lean / G6 repeatable: PARTIAL** — the 电脑管家 Qt side used vision-located client coords
  (not a deterministic widget tree) and a manual PowerShell PostMessage helper (not yet a repeatable
  naturo script). **Next: build a naturo Qt provider** (inject → enumerate `qApp->topLevelWidgets()`
  QObject tree for deterministic refs/geometry; operate via PostMessage/Qt-event) so 电脑管家 (and every
  Qt app: WPS/Navicat/为知/富途…) gets a deterministic, repeatable, token-lean tree. Authorized as
  naturo dev work under [[project_naturo_software_support_mission]].
