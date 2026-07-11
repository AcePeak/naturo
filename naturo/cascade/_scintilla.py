"""Scintilla text provider — read the content of Scintilla-based editors.

Notepad++, SciTE, and many IDEs render their editor with the **Scintilla**
control which — like Excel's grid — is opaque to UIA/MSAA: a UIA-only tool sees
the editor *pane* but none of the text. This provider finds the Scintilla child
window(s) of a target window and reads the full document via Scintilla's own
message API (``SCI_GETLENGTH`` / ``SCI_GETTEXT``) across the process boundary,
emitting it as a ``scintilla``-tagged (deterministic) node. It is naturo's moat
on Scintilla editors, mirroring the CDP (web), JAB (Java) and COM (Excel)
providers.

Windows-only; degrades to an empty result on any failure (never raises into the
cascade).
"""
from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes
from typing import List, Optional

from naturo.backends.base import ElementInfo

logger = logging.getLogger(__name__)

# Scintilla messages (Scintilla.h).
_SCI_GETLENGTH = 2006
_SCI_GETTEXT = 2182

_SCINTILLA_CLASS = "Scintilla"
#: Upper bound on bytes read from one editor (a giant file must not blow memory).
_MAX_SCINTILLA_BYTES = 8 * 1024 * 1024

# Win32 process/memory constants.
_PROCESS_VM_OPERATION = 0x0008
_PROCESS_VM_READ = 0x0010
_PROCESS_VM_WRITE = 0x0020
_MEM_COMMIT = 0x1000
_MEM_RESERVE = 0x2000
_MEM_RELEASE = 0x8000
_PAGE_READWRITE = 0x04


def _win32():
    """Return (user32, kernel32) with the signatures this module needs, or None."""
    try:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    except Exception:
        return None

    user32.SendMessageW.restype = ctypes.c_ssize_t
    user32.SendMessageW.argtypes = [
        wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t,
    ]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.VirtualAllocEx.restype = ctypes.c_void_p
    kernel32.VirtualAllocEx.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
        wintypes.DWORD, wintypes.DWORD,
    ]
    kernel32.VirtualFreeEx.restype = wintypes.BOOL
    kernel32.VirtualFreeEx.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wintypes.DWORD,
    ]
    kernel32.ReadProcessMemory.restype = wintypes.BOOL
    kernel32.ReadProcessMemory.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    return user32, kernel32


def _find_scintilla_windows(hwnd: int) -> List[tuple]:
    """Return ``[(sci_hwnd, (x, y, w, h)), …]`` — Scintilla children, biggest first."""
    win = _win32()
    if win is None or not hwnd:
        return []
    user32 = win[0]
    found: List[tuple] = []
    buf = ctypes.create_unicode_buffer(64)

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _cb(child, _lparam):
        user32.GetClassNameW(child, buf, 64)
        if buf.value == _SCINTILLA_CLASS:
            r = wintypes.RECT()
            user32.GetWindowRect(child, ctypes.byref(r))
            found.append((child, (r.left, r.top, r.right - r.left, r.bottom - r.top)))
        return True

    try:
        user32.EnumChildWindows(wintypes.HWND(hwnd), _cb, 0)
    except Exception as exc:
        logger.debug("Scintilla: EnumChildWindows failed: %s", exc)
        return []
    found.sort(key=lambda t: t[1][2] * t[1][3], reverse=True)
    return found


def _read_scintilla_text(sci_hwnd: int) -> Optional[str]:
    """Read a Scintilla control's full document text across the process boundary.

    Scintilla stores text as bytes (UTF-8 in Notepad++/most editors); SCI_GETTEXT
    writes into a caller buffer, so cross-process we allocate that buffer inside
    the target process (VirtualAllocEx) and read it back (ReadProcessMemory).
    """
    win = _win32()
    if win is None:
        return None
    user32, kernel32 = win

    length = int(user32.SendMessageW(sci_hwnd, _SCI_GETLENGTH, 0, 0))
    if length <= 0:
        return "" if length == 0 else None
    if length > _MAX_SCINTILLA_BYTES:
        length = _MAX_SCINTILLA_BYTES

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(sci_hwnd, ctypes.byref(pid))
    if not pid.value:
        return None

    proc = kernel32.OpenProcess(
        _PROCESS_VM_OPERATION | _PROCESS_VM_READ | _PROCESS_VM_WRITE,
        False, pid.value,
    )
    if not proc:
        logger.debug("Scintilla: OpenProcess failed for pid %s", pid.value)
        return None

    remote = None
    try:
        remote = kernel32.VirtualAllocEx(
            proc, None, length + 1, _MEM_COMMIT | _MEM_RESERVE, _PAGE_READWRITE,
        )
        if not remote:
            return None
        # SCI_GETTEXT(wParam = bufferLength, lParam = buffer) -> copies text + NUL.
        user32.SendMessageW(sci_hwnd, _SCI_GETTEXT, length + 1, remote)
        local = ctypes.create_string_buffer(length + 1)
        read = ctypes.c_size_t(0)
        ok = kernel32.ReadProcessMemory(
            proc, remote, local, length + 1, ctypes.byref(read),
        )
        if not ok:
            logger.debug("Scintilla: ReadProcessMemory failed")
            return None
        raw = local.raw[:length]
        return raw.decode("utf-8", errors="replace")
    finally:
        if remote:
            kernel32.VirtualFreeEx(proc, remote, 0, _MEM_RELEASE)
        kernel32.CloseHandle(proc)


def is_scintilla_window(hwnd: int) -> bool:
    """True if ``hwnd`` hosts at least one Scintilla editor control."""
    return bool(_find_scintilla_windows(hwnd))


def fetch_scintilla_content(hwnd: int) -> List[ElementInfo]:
    """Return one ``scintilla``-tagged Document node per editor, carrying its text.

    Empty list on any failure (no Scintilla, permission denied, etc.) — the
    cascade treats it like an unavailable provider.
    """
    nodes: List[ElementInfo] = []
    for i, (sci_hwnd, (x, y, w, h)) in enumerate(_find_scintilla_windows(hwnd)):
        try:
            text = _read_scintilla_text(sci_hwnd)
        except Exception as exc:
            logger.debug("Scintilla: read failed for hwnd %s: %s", sci_hwnd, exc)
            continue
        if not text:
            continue
        nodes.append(ElementInfo(
            id=f"scintilla_{sci_hwnd}",
            role="Document",
            name="Scintilla editor" if i == 0 else f"Scintilla editor {i + 1}",
            value=text,
            x=x, y=y, width=max(0, w), height=max(0, h),
            children=[],
            properties={"source": "scintilla", "readable": True, "editable": True},
        ))
    return nodes
