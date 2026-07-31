"""Drive a standard Win32/NSIS installer wizard via naturo (see -> click advance).

Usage: python drive_installer.py "<title-substr>" [max_steps]
Loops: resolve the installer window by title substring, `naturo see` it, find the
primary advance button (下一步/我接受/安装/Install/Next/Agree/完成/Finish — never
Cancel/取消), click it by ref, repeat until the window is gone or max_steps.
Prints each step. Foregrounds the window first (AttachThreadInput) so clicks land.
"""
import ctypes
import ctypes.wintypes as wt
import re
import subprocess
import sys
import time

TITLE = sys.argv[1] if len(sys.argv) > 1 else "安装"
MAX = int(sys.argv[2]) if len(sys.argv) > 2 else 10

ADVANCE = ["OK", "确定", "下一页", "我接受", "同意", "下一步", "安装(", "安装 ", "开始安装", "立即安装",
           "完成", "结束", "关闭(", "Install", "Next", "I Agree", "Agree", "Finish", "Done", "Close"]
AVOID = ["取消", "Cancel", "上一步", "Back", "跳过", "浏览", "Browse", "最小化",
         "最大化", "打开", "显示细节", "Details"]
u = ctypes.windll.user32


def find_win(substr):
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)
    def cb(h, _):
        if u.IsWindowVisible(h):
            n = u.GetWindowTextLengthW(h)
            b = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(h, b, n + 1)
            if substr in b.value:
                found.append((h, b.value))
        return True
    u.EnumWindows(cb, 0)
    return found[0] if found else None


def foreground(h):
    fg = u.GetForegroundWindow()
    t1 = u.GetWindowThreadProcessId(fg, None)
    t2 = u.GetWindowThreadProcessId(h, None)
    u.AttachThreadInput(t2, t1, True)
    u.BringWindowToTop(h)
    u.ShowWindow(h, 5)
    u.SetForegroundWindow(h)
    u.AttachThreadInput(t2, t1, False)
    time.sleep(0.3)


def see(h):
    out = subprocess.run(["python", "-m", "naturo", "see", "--hwnd", str(h)],
                         capture_output=True, text=True, encoding="utf-8",
                         errors="ignore").stdout
    # lines like: [Button] "OK" (...) e5 [uia] [a]
    btns = []
    radios = []
    for line in out.splitlines():
        m = re.search(r'\[Button\]\s+"([^"]*)".*?(e\d+)', line)
        if m:
            btns.append((m.group(1), m.group(2)))
        r = re.search(r'\[(?:RadioButton|CheckBox)\]\s+"([^"]*)".*?(e\d+)', line)
        if r:
            nm = r.group(1)
            accept = any(k in nm for k in ("我接受", "我同意", "接受协议", "同意此", "I accept", "Agree"))
            decline = any(k in nm for k in ("不接受", "不同意", "don't", "Don't", "not accept"))
            if accept and not decline:
                radios.append((nm, r.group(2)))
    return btns, radios


for step in range(1, MAX + 1):
    w = find_win(TITLE)
    if not w:
        print(f"[{step}] window '{TITLE}' gone -> installer finished")
        break
    h, title = w
    foreground(h)
    btns, radios = see(h)
    if radios:
        rname, rref = radios[0]
        subprocess.run(["python","-m","naturo","click",rref],capture_output=True,text=True)
        print(f"[{step}] accepted license radio {rref} '{rname}'"); time.sleep(0.6)
    # pick advance button not in AVOID
    target = None
    for name, ref in btns:
        if any(a in name for a in AVOID):
            continue
        if any(a in name for a in ADVANCE):
            target = (name, ref)
            break
    if not target:
        print(f"[{step}] '{title}': no advance button among {[b[0] for b in btns]}")
        break
    name, ref = target
    r = subprocess.run(["python", "-m", "naturo", "click", ref],
                       capture_output=True, text=True, encoding="utf-8", errors="ignore")
    print(f"[{step}] '{title}' -> clicked {ref} '{name}'")
    time.sleep(2.5)
