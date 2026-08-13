"""Win32 API function hooking for naturo (issue #40).

This package exposes the native MinHook-backed hooking engine (see
``core/src/hooks``) to Python:

* :class:`~naturo.hooks.manager.HookManager` — install / list / remove
  in-process hooks on supported Win32 APIs and drain the monitored-call log,
  over the ``naturo_core`` ctypes bridge.
* :mod:`naturo.hooks.injector` — cross-process ``LoadLibraryW`` DLL injection
  (``CreateRemoteThread``) with an administrator pre-flight check, used to load
  ``naturo_core`` into another process so the same hook API runs there.

In-process hooking works within the current process without elevation.
Cross-process injection loads code into a *different* process and requires
administrator privileges; it must only ever target processes the operator owns.
"""
from __future__ import annotations

from naturo.hooks.manager import (
    HOOK_ACTIONS,
    HookError,
    HookManager,
)
from naturo.hooks.injector import (
    HookInjectionError,
    inject_dll,
    is_admin,
)

__all__ = [
    "HOOK_ACTIONS",
    "HookError",
    "HookManager",
    "HookInjectionError",
    "inject_dll",
    "is_admin",
]
