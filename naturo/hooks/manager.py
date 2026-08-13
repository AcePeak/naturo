"""Hook lifecycle management over the naturo_core ctypes bridge (#40).

:class:`HookManager` is a thin, validated domain wrapper around the native
``naturo_hook_*`` exports (implemented in ``core/src/hooks/hook_manager.cpp``
on top of vendored MinHook). It installs, lists, and removes in-process hooks
on a curated set of resolvable Win32 APIs, and drains the thread-safe
monitored-call log the native layer keeps.

The manager holds no hook state itself — the native core is the single source
of truth (so a hook survives across manager instances within a process). This
keeps the Python layer stateless and easy to test: inject a fake ``core`` and
assert the calls.
"""
from __future__ import annotations

from typing import Any, List, Optional

# The two hook actions the native layer understands.
#   "log"   — record the call, then forward to the real API.
#   "block" — record the call, then return a per-API sentinel without forwarding.
HOOK_ACTIONS = ("log", "block")


class HookError(Exception):
    """Raised for invalid hook requests or native hook failures."""


def _load_core() -> Any:
    """Instantiate the native ``NaturoCore`` bridge (import kept lazy)."""
    from naturo.bridge import NaturoCore

    return NaturoCore()


class HookManager:
    """Install, list, remove, and monitor in-process Win32 API hooks.

    Args:
        core: An object exposing the ``hook_*`` methods of
            :class:`naturo.bridge.NaturoCore`. Defaults to a freshly loaded
            ``NaturoCore``. Injecting a stub here makes the manager fully
            unit-testable without the native DLL.
    """

    def __init__(self, core: Optional[Any] = None) -> None:
        self._core = core

    @property
    def core(self) -> Any:
        """The native bridge, loaded lazily on first use."""
        if self._core is None:
            self._core = _load_core()
        return self._core

    @staticmethod
    def _validate_action(action: str) -> str:
        """Normalize and validate a hook action, raising on an unknown value."""
        normalized = (action or "").lower()
        if normalized not in HOOK_ACTIONS:
            raise HookError(
                f"Unknown hook action {action!r}; expected one of {', '.join(HOOK_ACTIONS)}."
            )
        return normalized

    @staticmethod
    def _require(name: str, value: str) -> str:
        """Reject an empty module/function name with a clear message."""
        if not value or not value.strip():
            raise HookError(f"{name} must be a non-empty name.")
        return value

    @staticmethod
    def _canonical_module(module: str) -> str:
        """Normalize a module name to the native display form (``name.dll``)."""
        m = module.strip().lower()
        return m if m.endswith(".dll") else m + ".dll"

    def install(self, module: str, function: str, action: str = "log") -> dict[str, Any]:
        """Install (or re-arm) a hook on a supported Win32 API.

        Args:
            module: Module/DLL name (e.g. ``"user32"`` or ``"user32.dll"``).
            function: Exported function name (e.g. ``"MessageBoxW"``).
            action: ``"log"`` to record and forward, ``"block"`` to record and
                return the API's sentinel without forwarding.

        Returns:
            A dict describing the installed hook: ``{"module", "function",
            "action"}``.

        Raises:
            HookError: On an invalid argument or a native hook failure.
        """
        module = self._require("module", module)
        function = self._require("function", function)
        action = self._validate_action(action)
        try:
            self.core.hook_install(module, function, action)
        except Exception as exc:  # NaturoCoreError or bridge/load failure
            raise HookError(str(exc)) from exc
        return {
            "module": self._canonical_module(module),
            "function": function,
            "action": action,
        }

    def list(self) -> List[dict[str, Any]]:
        """Return the currently installed hooks.

        Returns:
            A list of ``{"module", "function", "action", "call_count"}`` dicts.

        Raises:
            HookError: On a native failure.
        """
        try:
            return self.core.hook_list()
        except Exception as exc:
            raise HookError(str(exc)) from exc

    def remove(self, module: str, function: str) -> bool:
        """Remove a previously installed hook.

        Args:
            module: Module/DLL name.
            function: Exported function name.

        Returns:
            True if a hook was removed, False if none was installed.

        Raises:
            HookError: On an invalid argument or a native failure.
        """
        module = self._require("module", module)
        function = self._require("function", function)
        try:
            return bool(self.core.hook_remove(module, function))
        except Exception as exc:
            raise HookError(str(exc)) from exc

    def monitor(self) -> List[dict[str, Any]]:
        """Drain and return the monitored-call log (clears the native buffer).

        Returns:
            A list of ``{"seq", "module", "function", "action", "detail"}``
            records, ordered oldest-first.

        Raises:
            HookError: On a native failure.
        """
        try:
            return self.core.hook_drain_log()
        except Exception as exc:
            raise HookError(str(exc)) from exc

    def supported(self) -> List[dict[str, Any]]:
        """Return the Win32 APIs this native build can hook.

        Returns:
            A list of ``{"module", "function"}`` dicts.

        Raises:
            HookError: On a native failure.
        """
        try:
            return self.core.hook_supported()
        except Exception as exc:
            raise HookError(str(exc)) from exc

    def clear(self) -> None:
        """Remove every installed hook and clear the monitored-call log.

        Raises:
            HookError: On a native failure.
        """
        try:
            self.core.hook_clear()
        except Exception as exc:
            raise HookError(str(exc)) from exc
