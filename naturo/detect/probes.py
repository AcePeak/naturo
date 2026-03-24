"""Framework detection probes.

Each probe function checks whether a specific UI framework / interaction
method is available for a given process. Probes are designed to be fast
and non-destructive — they inspect process metadata without modifying state.

All probes follow the signature:
    probe_xxx(pid: int, exe: str, hwnd: Optional[int]) -> Optional[InteractionMethod]

Returns an InteractionMethod if the method is available, None otherwise.
"""

import logging
import os
import platform
import sys
from typing import List, Optional, Set

from naturo.detect.models import (
    FrameworkInfo,
    FrameworkType,
    InteractionMethod,
    InteractionMethodType,
    METHOD_PRIORITY,
    ProbeStatus,
)

logger = logging.getLogger(__name__)

# Cached NaturoCore instance for probes (avoids repeated DLL load + init)
_native_core = None


def _get_native_core():
    """Return a lazily-initialized NaturoCore instance.

    The C++ DLL requires ``naturo_init()`` (COM initialization) before
    UIA calls work.  Without it, ``get_element_tree`` silently fails
    and returns None — the root cause of #208.

    Returns:
        Initialized NaturoCore singleton.
    """
    global _native_core
    if _native_core is None:
        from naturo.bridge import NaturoCore
        _native_core = NaturoCore()
        _native_core.init()
    return _native_core


# DLL signatures for framework detection
_ELECTRON_DLLS = {"electron.exe", "libcef.dll", "chrome_elf.dll"}
_CEF_DLLS = {"libcef.dll"}
_CHROME_DLLS = {"chrome.dll", "chrome_elf.dll"}
_WPF_DLLS = {"presentationframework.dll", "presentationcore.dll", "wpfgfx_v0400.dll"}
_WINFORMS_DLLS = {"system.windows.forms.dll"}
_QT_DLLS = {"qt5core.dll", "qt6core.dll", "qt5widgets.dll", "qt6widgets.dll"}
_JAVA_DLLS = {"jvm.dll", "java.dll"}
_JAB_DLLS = {"windowsaccessbridge-64.dll", "windowsaccessbridge-32.dll", "windowsaccessbridge.dll"}
_GTK_DLLS = {"libgtk-3-0.dll", "libgtk-4-1.dll"}


def _get_process_dlls(pid: int) -> Set[str]:
    """Get the set of loaded DLL names for a process (lowercase).

    Args:
        pid: Process ID to inspect.

    Returns:
        Set of lowercase DLL filenames loaded by the process.
    """
    if platform.system() != "Windows":
        return set()

    try:
        import ctypes
        from ctypes import wintypes

        # Use EnumProcessModulesEx via psapi
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        PROCESS_QUERY_INFORMATION = 0x0400
        PROCESS_VM_READ = 0x0010

        h_process = kernel32.OpenProcess(
            PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid
        )
        if not h_process:
            return set()

        try:
            h_mods = (ctypes.c_void_p * 1024)()
            cb_needed = wintypes.DWORD()
            LIST_MODULES_ALL = 0x03

            if not psapi.EnumProcessModulesEx(
                h_process, h_mods, ctypes.sizeof(h_mods),
                ctypes.byref(cb_needed), LIST_MODULES_ALL
            ):
                return set()

            num_mods = cb_needed.value // ctypes.sizeof(ctypes.c_void_p)
            dlls = set()
            mod_name = ctypes.create_unicode_buffer(260)

            for i in range(num_mods):
                if psapi.GetModuleFileNameExW(
                    h_process, h_mods[i], mod_name, 260
                ):
                    name = os.path.basename(mod_name.value).lower()
                    dlls.add(name)

            return dlls
        finally:
            kernel32.CloseHandle(h_process)

    except Exception as exc:
        logger.debug("Failed to enumerate DLLs for PID %d: %s", pid, exc)
        return set()


def detect_frameworks_from_dlls(pid: int, exe: str) -> List[FrameworkInfo]:
    """Detect frameworks by scanning loaded DLLs.

    Args:
        pid: Process ID.
        exe: Executable path.

    Returns:
        List of detected FrameworkInfo objects.
    """
    dlls = _get_process_dlls(pid)
    if not dlls:
        # On non-Windows or if DLL scan fails, try to infer from exe name
        exe_lower = exe.lower()
        frameworks = []
        if "electron" in exe_lower:
            frameworks.append(FrameworkInfo(
                framework_type=FrameworkType.ELECTRON,
                dll_signatures=["(inferred from exe name)"],
            ))
        elif "chrome" in exe_lower or "chromium" in exe_lower:
            frameworks.append(FrameworkInfo(
                framework_type=FrameworkType.CHROME,
                dll_signatures=["(inferred from exe name)"],
            ))
        elif "java" in exe_lower or "javaw" in exe_lower:
            frameworks.append(FrameworkInfo(
                framework_type=FrameworkType.JAVA_SWING,
                dll_signatures=["(inferred from exe name)"],
            ))
        return frameworks

    frameworks = []

    # Check for Electron (must check before generic Chrome/CEF)
    electron_matches = dlls & _ELECTRON_DLLS
    if electron_matches and ("electron.exe" in dlls or
                             (dlls & _CEF_DLLS and "chrome.dll" not in dlls)):
        frameworks.append(FrameworkInfo(
            framework_type=FrameworkType.ELECTRON,
            dll_signatures=sorted(electron_matches),
        ))

    # CEF (without Electron)
    cef_matches = dlls & _CEF_DLLS
    if cef_matches and not any(f.framework_type == FrameworkType.ELECTRON for f in frameworks):
        if "chrome.dll" not in dlls:  # Not Chrome browser itself
            frameworks.append(FrameworkInfo(
                framework_type=FrameworkType.CEF,
                dll_signatures=sorted(cef_matches),
            ))

    # Chrome browser
    if "chrome.dll" in dlls:
        frameworks.append(FrameworkInfo(
            framework_type=FrameworkType.CHROME,
            dll_signatures=sorted(dlls & _CHROME_DLLS),
        ))

    # WPF
    wpf_matches = dlls & _WPF_DLLS
    if wpf_matches:
        frameworks.append(FrameworkInfo(
            framework_type=FrameworkType.WPF,
            dll_signatures=sorted(wpf_matches),
        ))

    # WinForms
    winforms_matches = dlls & _WINFORMS_DLLS
    if winforms_matches:
        frameworks.append(FrameworkInfo(
            framework_type=FrameworkType.WINFORMS,
            dll_signatures=sorted(winforms_matches),
        ))

    # Qt
    qt_matches = dlls & _QT_DLLS
    if qt_matches:
        version = "6" if any("qt6" in d for d in qt_matches) else "5"
        frameworks.append(FrameworkInfo(
            framework_type=FrameworkType.QT,
            version=f"Qt {version}",
            dll_signatures=sorted(qt_matches),
        ))

    # Java
    java_matches = dlls & _JAVA_DLLS
    if java_matches:
        fw_type = FrameworkType.JAVA_SWING  # Default assumption
        frameworks.append(FrameworkInfo(
            framework_type=fw_type,
            dll_signatures=sorted(java_matches),
        ))

    # GTK
    gtk_matches = dlls & _GTK_DLLS
    if gtk_matches:
        frameworks.append(FrameworkInfo(
            framework_type=FrameworkType.GTK,
            dll_signatures=sorted(gtk_matches),
        ))

    # If nothing detected, mark as unknown Win32
    if not frameworks:
        frameworks.append(FrameworkInfo(
            framework_type=FrameworkType.WIN32 if platform.system() == "Windows" else FrameworkType.UNKNOWN,
        ))

    return frameworks


def probe_cdp(pid: int, exe: str, hwnd: Optional[int] = None) -> Optional[InteractionMethod]:
    """Probe for Chrome DevTools Protocol availability.

    Checks if the process has a CDP debug port open. Works for Electron,
    CEF, and Chrome browser processes.

    Args:
        pid: Process ID.
        exe: Executable path.
        hwnd: Window handle (unused for CDP).

    Returns:
        InteractionMethod if CDP is available, None otherwise.
    """
    if platform.system() != "Windows":
        return None

    try:
        # Try to find debug port from command line args
        debug_port = _find_cdp_debug_port(pid)
        if debug_port:
            return InteractionMethod(
                method=InteractionMethodType.CDP,
                priority=METHOD_PRIORITY[InteractionMethodType.CDP],
                status=ProbeStatus.AVAILABLE,
                capabilities=["dom", "click", "type", "evaluate", "screenshot", "network"],
                metadata={"debug_port": debug_port},
                confidence=0.95,
            )

        # Check if process is Electron/CEF (could potentially enable CDP)
        dlls = _get_process_dlls(pid)
        if dlls & (_ELECTRON_DLLS | _CEF_DLLS):
            return InteractionMethod(
                method=InteractionMethodType.CDP,
                priority=METHOD_PRIORITY[InteractionMethodType.CDP],
                status=ProbeStatus.UNAVAILABLE,
                capabilities=["dom", "click", "type", "evaluate", "screenshot", "network"],
                metadata={"note": "Electron/CEF detected but no debug port. Relaunch with --remote-debugging-port=<port> to enable."},
                confidence=0.0,
            )

    except Exception as exc:
        logger.debug("CDP probe failed for PID %d: %s", pid, exc)

    return None


def _find_cdp_debug_port(pid: int) -> Optional[int]:
    """Find the CDP debug port from process command line.

    Args:
        pid: Process ID.

    Returns:
        Debug port number if found, None otherwise.
    """
    if platform.system() != "Windows":
        return None

    try:
        import ctypes
        from ctypes import wintypes
        import subprocess

        # Use wmic to get command line (most reliable on Windows)
        result = subprocess.run(
            ["wmic", "process", "where", f"ProcessId={pid}",
             "get", "CommandLine", "/format:list"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "--remote-debugging-port=" in line:
                    for part in line.split():
                        if part.startswith("--remote-debugging-port="):
                            port_str = part.split("=", 1)[1]
                            return int(port_str)
    except Exception as exc:
        logger.debug("Failed to get command line for PID %d: %s", pid, exc)

    # Also check common debug ports by trying to connect
    import socket
    for port in [9222, 9229, 9333]:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if result == 0:
                return port
        except Exception:
            pass

    return None


def probe_uia(pid: int, exe: str, hwnd: Optional[int] = None) -> Optional[InteractionMethod]:
    """Probe for UI Automation availability.

    Checks if the process window is accessible via UIA.

    Args:
        pid: Process ID.
        exe: Executable path.
        hwnd: Window handle to test (if known).

    Returns:
        InteractionMethod if UIA is available, None otherwise.
    """
    if platform.system() != "Windows":
        return None

    target_hwnd = hwnd or _find_main_window(pid)
    if not target_hwnd:
        return None

    # Strategy 1: Use the native C++ DLL (same path as 'naturo see').
    # This is the primary UIA pathway and doesn't require comtypes.
    try:
        core = _get_native_core()
        tree = core.get_element_tree(hwnd=target_hwnd, depth=1)
        if tree is not None:
            capabilities = ["click", "type", "find", "tree", "screenshot"]
            return InteractionMethod(
                method=InteractionMethodType.UIA,
                priority=METHOD_PRIORITY[InteractionMethodType.UIA],
                status=ProbeStatus.AVAILABLE,
                capabilities=capabilities,
                confidence=0.95,
            )
        else:
            logger.debug(
                "UIA probe via native DLL returned empty tree for PID %d (hwnd=%s)",
                pid, target_hwnd,
            )
    except Exception as exc:
        logger.debug("UIA probe via native DLL failed for PID %d: %s", pid, exc)

    # Strategy 2: Fall back to comtypes if native DLL is unavailable.
    try:
        import comtypes.client  # type: ignore

        # Ensure gen modules are initialized before importing (#200).
        try:
            from comtypes.gen.UIAutomationClient import IUIAutomation as _IUIAutomation  # type: ignore
        except (ImportError, ModuleNotFoundError):
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen.UIAutomationClient import IUIAutomation as _IUIAutomation  # type: ignore

        uia = comtypes.client.CreateObject(
            "{ff48dba4-60ef-4201-aa87-54103eef594e}",
            interface=_IUIAutomation,
        )

        element = uia.ElementFromHandle(target_hwnd)
        if element:
            capabilities = ["click", "type", "find", "tree", "screenshot"]

            return InteractionMethod(
                method=InteractionMethodType.UIA,
                priority=METHOD_PRIORITY[InteractionMethodType.UIA],
                status=ProbeStatus.AVAILABLE,
                capabilities=capabilities,
                confidence=0.9,
            )

    except ImportError:
        logger.debug("comtypes not available for UIA probe — install with: pip install comtypes")
    except Exception as exc:
        logger.debug("UIA probe via comtypes failed for PID %d: %s", pid, exc)

    return None


def probe_msaa(pid: int, exe: str, hwnd: Optional[int] = None) -> Optional[InteractionMethod]:
    """Probe for MSAA (Microsoft Active Accessibility) availability.

    Args:
        pid: Process ID.
        exe: Executable path.
        hwnd: Window handle to test.

    Returns:
        InteractionMethod if MSAA is available, None otherwise.
    """
    if platform.system() != "Windows":
        return None

    try:
        import ctypes
        oleacc = ctypes.WinDLL("oleacc", use_last_error=True)

        target_hwnd = hwnd or _find_main_window(pid)
        if not target_hwnd:
            return None

        # Try AccessibleObjectFromWindow
        OBJID_WINDOW = 0x00000000
        p_acc = ctypes.c_void_p()
        iid_accessible = (ctypes.c_byte * 16)(
            0x61, 0x80, 0x36, 0x61, 0x00, 0x00, 0xCF, 0x11,
            0xBD, 0x01, 0x00, 0xAA, 0x00, 0x55, 0x59, 0x5A,
        )

        hr = oleacc.AccessibleObjectFromWindow(
            target_hwnd, OBJID_WINDOW,
            ctypes.byref((ctypes.c_byte * 16)(*iid_accessible)),
            ctypes.byref(p_acc),
        )

        if hr == 0 and p_acc.value:
            return InteractionMethod(
                method=InteractionMethodType.MSAA,
                priority=METHOD_PRIORITY[InteractionMethodType.MSAA],
                status=ProbeStatus.AVAILABLE,
                capabilities=["click", "type", "find"],
                confidence=0.7,
            )

    except Exception as exc:
        logger.debug("MSAA probe failed for PID %d: %s", pid, exc)

    return None


def probe_jab(pid: int, exe: str, hwnd: Optional[int] = None) -> Optional[InteractionMethod]:
    """Probe for Java Access Bridge availability.

    Args:
        pid: Process ID.
        exe: Executable path.
        hwnd: Window handle.

    Returns:
        InteractionMethod if JAB is available, None otherwise.
    """
    if platform.system() != "Windows":
        return None

    # Check if Java DLLs are loaded
    dlls = _get_process_dlls(pid)
    if not (dlls & _JAVA_DLLS):
        return None

    # Check if JAB bridge DLLs are present
    has_jab = bool(dlls & _JAB_DLLS)
    if has_jab:
        return InteractionMethod(
            method=InteractionMethodType.JAB,
            priority=METHOD_PRIORITY[InteractionMethodType.JAB],
            status=ProbeStatus.AVAILABLE,
            capabilities=["click", "type", "find", "tree"],
            metadata={"jab_dlls": sorted(dlls & _JAB_DLLS)},
            confidence=0.8,
        )
    else:
        return InteractionMethod(
            method=InteractionMethodType.JAB,
            priority=METHOD_PRIORITY[InteractionMethodType.JAB],
            status=ProbeStatus.UNAVAILABLE,
            capabilities=["click", "type", "find", "tree"],
            metadata={"note": "Java app detected but JAB not enabled. Enable via jabswitch.exe or Control Panel > Accessibility."},
            confidence=0.0,
        )


def probe_ia2(pid: int, exe: str, hwnd: Optional[int] = None) -> Optional[InteractionMethod]:
    """Probe for IAccessible2 availability.

    IAccessible2 is used by Firefox, LibreOffice, Thunderbird.

    Args:
        pid: Process ID.
        exe: Executable path.
        hwnd: Window handle.

    Returns:
        InteractionMethod if IA2 is available, None otherwise.
    """
    if platform.system() != "Windows":
        return None

    # Heuristic: check exe name for known IA2 apps
    exe_lower = os.path.basename(exe).lower()
    ia2_apps = {"firefox.exe", "thunderbird.exe", "soffice.exe", "soffice.bin"}

    if exe_lower in ia2_apps:
        return InteractionMethod(
            method=InteractionMethodType.IA2,
            priority=METHOD_PRIORITY[InteractionMethodType.IA2],
            status=ProbeStatus.AVAILABLE,
            capabilities=["click", "type", "find", "tree"],
            confidence=0.85,
        )

    return None


def probe_vision(pid: int, exe: str, hwnd: Optional[int] = None) -> InteractionMethod:
    """Vision probe — always available as fallback.

    Uses screenshot + AI-based element detection. Works on any application
    but is slower and less precise than native methods.

    Args:
        pid: Process ID.
        exe: Executable path.
        hwnd: Window handle.

    Returns:
        InteractionMethod (always returns, as vision is always a fallback).
    """
    return InteractionMethod(
        method=InteractionMethodType.VISION,
        priority=METHOD_PRIORITY[InteractionMethodType.VISION],
        status=ProbeStatus.FALLBACK,
        capabilities=["click", "screenshot"],
        confidence=0.5,
    )


def _find_main_window(pid: int) -> Optional[int]:
    """Find the main window handle for a process.

    For UWP apps hosted by ApplicationFrameHost.exe, the visible window
    belongs to ApplicationFrameHost, not the actual app process (e.g.,
    CalculatorApp.exe).  When no direct match is found, this function
    checks for an ApplicationFrameHost window whose child process matches
    the target PID (#249).

    Args:
        pid: Process ID.

    Returns:
        Window handle (HWND) or None if not found.
    """
    if platform.system() != "Windows":
        return None

    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        found_hwnd = ctypes.c_void_p(0)
        frame_hwnds: list = []  # ApplicationFrameHost windows

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def enum_callback(hwnd, lparam):
            window_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            if not user32.IsWindowVisible(hwnd):
                return True

            if window_pid.value == pid:
                found_hwnd.value = hwnd
                return False  # Stop enumeration

            # Track ApplicationFrameHost windows for UWP fallback (#249)
            cls_buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, cls_buf, 256)
            if cls_buf.value == "ApplicationFrameWindow":
                frame_hwnds.append((int(hwnd), window_pid.value))

            return True

        user32.EnumWindows(enum_callback, 0)

        if found_hwnd.value:
            return found_hwnd.value

        # UWP fallback (#249): no direct window found for this PID.
        # Check if any ApplicationFrameHost window hosts a child whose
        # owning PID matches the target.  UWP apps have a child window
        # (class "Windows.UI.Core.CoreWindow") owned by the actual app
        # process inside the ApplicationFrameHost top-level window.
        if frame_hwnds:
            for frame_hwnd, _frame_pid in frame_hwnds:
                if _frame_hosts_pid(user32, frame_hwnd, pid):
                    return frame_hwnd

        return None

    except Exception as exc:
        logger.debug("Failed to find main window for PID %d: %s", pid, exc)
        return None


def _frame_hosts_pid(user32, frame_hwnd: int, target_pid: int) -> bool:
    """Check if an ApplicationFrameHost window hosts a child with the target PID.

    Enumerates child windows of the given frame window and checks if any
    belong to the target process.

    Args:
        user32: ctypes user32 DLL handle.
        frame_hwnd: Handle of the ApplicationFrameHost top-level window.
        target_pid: Process ID to look for among child windows.

    Returns:
        True if a child window owned by target_pid is found.
    """
    import ctypes
    from ctypes import wintypes

    found = ctypes.c_bool(False)

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def child_callback(child_hwnd, lparam):
        child_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(child_hwnd, ctypes.byref(child_pid))
        if child_pid.value == target_pid:
            found.value = True
            return False  # Stop enumeration
        return True

    user32.EnumChildWindows(frame_hwnd, child_callback, 0)
    return found.value
