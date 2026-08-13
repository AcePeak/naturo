"""Cross-process DLL injection for naturo hooks (#40).

Loads a DLL (in practice ``naturo_core``) into another process via the classic
``CreateRemoteThread`` + ``LoadLibraryW`` technique, so the in-process hook API
(:mod:`naturo.hooks.manager`) can run *inside* a target process and intercept
its Win32 calls.

Security posture
----------------
Injecting code into a process the current user does not own requires
administrator privileges (and, for protected processes, is refused by the OS
outright). :func:`inject_dll` performs an explicit ``is_admin`` pre-flight and
raises a clear :class:`HookInjectionError` when not elevated, rather than
failing deep inside a Win32 call with an opaque error code. Only ever target
processes you own and control — this is an operator tool for enterprise
automation, not a means to tamper with third-party software.

All Windows-only ctypes usage is guarded behind ``sys.platform == "win32"``
statements so the module imports and type-checks cleanly on non-Windows
platforms (where every entry point raises).
"""
from __future__ import annotations

import ctypes
import os
import sys
from typing import Any

# Win32 constants (kernel32).
_PROCESS_CREATE_THREAD = 0x0002
_PROCESS_QUERY_INFORMATION = 0x0400
_PROCESS_VM_OPERATION = 0x0008
_PROCESS_VM_WRITE = 0x0020
_PROCESS_VM_READ = 0x0010
_PROCESS_INJECT_ACCESS = (
    _PROCESS_CREATE_THREAD
    | _PROCESS_QUERY_INFORMATION
    | _PROCESS_VM_OPERATION
    | _PROCESS_VM_WRITE
    | _PROCESS_VM_READ
)
_MEM_COMMIT = 0x1000
_MEM_RESERVE = 0x2000
_MEM_RELEASE = 0x8000
_PAGE_READWRITE = 0x04
_INFINITE = 0xFFFFFFFF
_WAIT_TIMEOUT = 0x00000102


class HookInjectionError(Exception):
    """Raised when cross-process DLL injection cannot be performed."""


def is_admin() -> bool:
    """Return True if the current process is running elevated (Administrator).

    Returns False on any non-Windows platform and on any query failure (the
    conservative answer — callers should refuse to inject when this is False).
    """
    if sys.platform != "win32":
        return False
    if sys.platform == "win32":
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())  # type: ignore[attr-defined]
        except Exception:
            return False
    return False


def _check_last_error(ok: object, operation: str) -> None:
    """Raise HookInjectionError with the Win32 error when *ok* is falsy."""
    if ok:
        return
    if sys.platform == "win32":
        err = ctypes.get_last_error()
        raise HookInjectionError(f"{operation} failed (Win32 error {err}).")
    raise HookInjectionError(f"{operation} failed.")


def inject_dll(pid: int, dll_path: str, *, require_admin: bool = True,
               timeout_ms: int = 10000) -> None:
    """Inject a DLL into a target process by PID.

    Loads ``dll_path`` into process ``pid`` using ``CreateRemoteThread`` on
    ``LoadLibraryW``. The DLL's ``DllMain`` runs in the target on attach; for
    ``naturo_core`` this makes the ``naturo_hook_*`` exports available inside
    the target so its Win32 calls can be hooked.

    Args:
        pid: Target process id.
        dll_path: Absolute path to the DLL to inject. Must exist and be the
            same architecture (x64) as the target process.
        require_admin: When True (default), refuse to inject unless the current
            process is elevated. Injecting across security boundaries needs
            administrator rights; this surfaces that as a clear error instead of
            an opaque ``OpenProcess`` failure.
        timeout_ms: How long to wait for the remote ``LoadLibraryW`` thread.

    Raises:
        HookInjectionError: On a non-Windows platform, when not elevated (and
            ``require_admin``), when the DLL path is missing, or on any Win32
            failure during injection.
    """
    if sys.platform != "win32":
        raise HookInjectionError("DLL injection is only supported on Windows.")

    if not isinstance(pid, int) or pid <= 0:
        raise HookInjectionError(f"Invalid target pid: {pid!r}.")

    dll_path = os.path.abspath(dll_path)
    if not os.path.isfile(dll_path):
        raise HookInjectionError(f"DLL not found: {dll_path}")

    if require_admin and not is_admin():
        raise HookInjectionError(
            "Cross-process DLL injection requires administrator privileges. "
            "Re-run naturo from an elevated (Run as administrator) console, or "
            "pass require_admin=False only for a same-user target you own."
        )

    if sys.platform == "win32":
        _inject_win32(pid, dll_path, timeout_ms)


def _inject_win32(pid: int, dll_path: str, timeout_ms: int) -> None:
    """Windows implementation of :func:`inject_dll` (guarded by its callers)."""
    kernel32: Any = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]

    # Pointer-width-correct signatures (HANDLE/LPVOID are 64-bit on x64).
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel32.VirtualAllocEx.restype = ctypes.c_void_p
    kernel32.VirtualAllocEx.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32, ctypes.c_uint32,
    ]
    kernel32.WriteProcessMemory.restype = ctypes.c_int
    kernel32.WriteProcessMemory.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    kernel32.GetModuleHandleW.restype = ctypes.c_void_p
    kernel32.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel32.GetProcAddress.restype = ctypes.c_void_p
    kernel32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    kernel32.CreateRemoteThread.restype = ctypes.c_void_p
    kernel32.CreateRemoteThread.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32),
    ]
    kernel32.VirtualFreeEx.restype = ctypes.c_int
    kernel32.VirtualFreeEx.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32,
    ]
    kernel32.WaitForSingleObject.restype = ctypes.c_uint32
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel32.GetExitCodeThread.restype = ctypes.c_int
    kernel32.GetExitCodeThread.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
    kernel32.CloseHandle.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]

    # LoadLibraryW lives in kernel32, which loads at the same base in every
    # process, so its address in this process is valid in the target too.
    load_library = kernel32.GetProcAddress(
        kernel32.GetModuleHandleW("kernel32.dll"), b"LoadLibraryW"
    )
    _check_last_error(load_library, "GetProcAddress(LoadLibraryW)")

    h_process = kernel32.OpenProcess(_PROCESS_INJECT_ACCESS, 0, pid)
    _check_last_error(h_process, f"OpenProcess(pid={pid})")

    remote_mem = None
    h_thread = None
    try:
        path_bytes = (dll_path + "\x00").encode("utf-16-le")
        size = len(path_bytes)
        remote_mem = kernel32.VirtualAllocEx(
            h_process, None, size, _MEM_COMMIT | _MEM_RESERVE, _PAGE_READWRITE
        )
        _check_last_error(remote_mem, "VirtualAllocEx")

        written = ctypes.c_size_t(0)
        ok = kernel32.WriteProcessMemory(
            h_process, remote_mem, path_bytes, size, ctypes.byref(written)
        )
        _check_last_error(ok and written.value == size, "WriteProcessMemory")

        h_thread = kernel32.CreateRemoteThread(
            h_process, None, 0, load_library, remote_mem, 0, None
        )
        _check_last_error(h_thread, "CreateRemoteThread")

        wait = kernel32.WaitForSingleObject(h_thread, timeout_ms)
        if wait == _WAIT_TIMEOUT:
            raise HookInjectionError(
                f"Remote LoadLibraryW did not complete within {timeout_ms} ms."
            )

        exit_code = ctypes.c_uint32(0)
        kernel32.GetExitCodeThread(h_thread, ctypes.byref(exit_code))
        # LoadLibraryW returns the loaded module handle (truncated to the
        # thread exit code's 32 bits); zero means the load failed in the target.
        if exit_code.value == 0:
            raise HookInjectionError(
                "Remote LoadLibraryW returned NULL — the DLL failed to load in "
                "the target (check architecture match and dependencies)."
            )
    finally:
        if h_thread:
            kernel32.CloseHandle(h_thread)
        if remote_mem:
            kernel32.VirtualFreeEx(h_process, remote_mem, 0, _MEM_RELEASE)
        kernel32.CloseHandle(h_process)
