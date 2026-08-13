"""Hermetic tests for the Win32 API hooking feature (#40).

These tests exercise the Python hook layer WITHOUT the native ``naturo_core``
DLL and WITHOUT any real API hooking or cross-process injection:

* :class:`_FakeCore` models the native hook engine's observable contract
  (install/list/remove bookkeeping, a monitored-call log with a block action),
  so :class:`naturo.hooks.manager.HookManager` can be driven deterministically.
* The CLI tests parse ``naturo hook ...`` against a patched manager.
* The injector tests assert the administrator pre-flight and argument guards
  fire *before* any Win32 call — no process is ever opened or injected.

Live in-process hooking and cross-process injection are verified elsewhere (by
the orchestrator, on an isolated target); nothing here touches a real process.
"""
from __future__ import annotations

import sys

import pytest
from click.testing import CliRunner

from naturo.hooks.manager import HOOK_ACTIONS, HookError, HookManager

# The DLL-injection path is Windows-only: ``inject_dll`` raises immediately on a
# non-Windows platform, before the admin / dll-exists / pid guards it wraps. Gate
# those guard tests to Windows; a dedicated test below asserts the non-Windows
# rejection instead.
_WINDOWS_ONLY = pytest.mark.skipif(
    sys.platform != "win32", reason="Windows-only DLL injection path"
)


# ── A fake native core modelling the hook engine's contract ──────────────────


class _FakeCore:
    """In-memory stand-in for ``NaturoCore``'s ``hook_*`` methods.

    Mirrors the native semantics closely enough to test the manager:
    idempotent re-arm, a monitored-call log honoring the block action, and a
    curated supported-API list.
    """

    def __init__(self) -> None:
        self._hooks: dict[str, dict] = {}
        self._log: list[dict] = []
        self._seq = 0
        self.supported_apis = [
            {"module": "user32.dll", "function": "MessageBoxW"},
            {"module": "kernel32.dll", "function": "CreateFileW"},
        ]

    @staticmethod
    def _norm_module(module: str) -> str:
        m = module.lower()
        return m if m.endswith(".dll") else m + ".dll"

    def _key(self, module: str, function: str) -> str:
        return f"{self._norm_module(module)}!{function.lower()}"

    def _find_supported(self, module: str, function: str) -> dict | None:
        want_m = self._norm_module(module)
        for api in self.supported_apis:
            if self._norm_module(api["module"]) == want_m and \
                    api["function"].lower() == function.lower():
                return api
        return None

    # -- API mirrored from NaturoCore --

    def hook_install(self, module: str, function: str, action: str) -> None:
        api = self._find_supported(module, function)
        if api is None:
            raise ValueError(f"unsupported API {module}!{function}")  # native -1
        key = self._key(api["module"], api["function"])
        if key in self._hooks:
            self._hooks[key]["action"] = action  # re-arm
            return
        self._hooks[key] = {
            "module": api["module"], "function": api["function"],
            "action": action, "call_count": 0,
        }

    def hook_list(self) -> list[dict]:
        return [dict(h) for h in self._hooks.values()]

    def hook_remove(self, module: str, function: str) -> bool:
        key = self._key(module, function)
        return self._hooks.pop(key, None) is not None

    def hook_drain_log(self) -> list[dict]:
        drained = list(self._log)
        self._log.clear()
        return drained

    def hook_supported(self) -> list[dict]:
        return [dict(a) for a in self.supported_apis]

    def hook_clear(self) -> None:
        self._hooks.clear()
        self._log.clear()

    # -- test helper: simulate an intercepted call --

    def simulate_call(self, module: str, function: str, detail: str) -> bool:
        """Record a call as the native detour would; return True if blocked."""
        key = self._key(module, function)
        hook = self._hooks[key]
        hook["call_count"] += 1
        self._seq += 1
        self._log.append({
            "seq": self._seq, "module": hook["module"],
            "function": hook["function"], "action": hook["action"], "detail": detail,
        })
        return hook["action"] == "block"


@pytest.fixture()
def manager() -> HookManager:
    return HookManager(core=_FakeCore())


# ── Manager: install / list / remove bookkeeping ─────────────────────────────


def test_install_records_hook(manager: HookManager) -> None:
    info = manager.install("user32", "MessageBoxW", "log")
    assert info == {"module": "user32.dll", "function": "MessageBoxW", "action": "log"}
    hooks = manager.list()
    assert len(hooks) == 1
    assert hooks[0]["module"] == "user32.dll"
    assert hooks[0]["function"] == "MessageBoxW"
    assert hooks[0]["action"] == "log"
    assert hooks[0]["call_count"] == 0


def test_install_defaults_to_log(manager: HookManager) -> None:
    info = manager.install("user32", "MessageBoxW")
    assert info["action"] == "log"


def test_install_is_idempotent_rearm(manager: HookManager) -> None:
    manager.install("kernel32", "CreateFileW", "log")
    manager.install("kernel32", "CreateFileW", "block")  # re-arm, not duplicate
    hooks = manager.list()
    assert len(hooks) == 1
    assert hooks[0]["action"] == "block"


def test_module_suffix_and_case_insensitive(manager: HookManager) -> None:
    # "user32.dll" and "user32", any case, resolve to the same hook.
    manager.install("USER32.DLL", "MessageBoxW", "log")
    assert manager.remove("user32", "MessageBoxW") is True
    assert manager.list() == []


def test_remove_absent_returns_false(manager: HookManager) -> None:
    assert manager.remove("user32", "MessageBoxW") is False


def test_clear_removes_all(manager: HookManager) -> None:
    manager.install("user32", "MessageBoxW", "log")
    manager.install("kernel32", "CreateFileW", "log")
    manager.clear()
    assert manager.list() == []


def test_supported_lists_apis(manager: HookManager) -> None:
    apis = manager.supported()
    assert {"module": "user32.dll", "function": "MessageBoxW"} in apis


# ── Manager: monitor log drain + block sentinel semantics ────────────────────


def test_monitor_drains_and_clears(manager: HookManager) -> None:
    core: _FakeCore = manager.core  # type: ignore[assignment]
    manager.install("kernel32", "CreateFileW", "log")
    core.simulate_call("kernel32", "CreateFileW", 'path="a.txt"')
    core.simulate_call("kernel32", "CreateFileW", 'path="b.txt"')

    events = manager.monitor()
    assert [e["detail"] for e in events] == ['path="a.txt"', 'path="b.txt"']
    assert all(e["action"] == "log" for e in events)
    # Draining clears the buffer.
    assert manager.monitor() == []


def test_block_action_is_recorded_and_blocks(manager: HookManager) -> None:
    core: _FakeCore = manager.core  # type: ignore[assignment]
    manager.install("kernel32", "CreateFileW", "block")
    blocked = core.simulate_call("kernel32", "CreateFileW", 'path="secret"')
    assert blocked is True  # the detour returns the sentinel instead of forwarding
    events = manager.monitor()
    assert len(events) == 1
    assert events[0]["action"] == "block"
    # call_count is tracked on the live hook.
    assert manager.list()[0]["call_count"] == 1


# ── Manager: validation ──────────────────────────────────────────────────────


@pytest.mark.parametrize("bad", ["", "warn", "LOGG", "drop"])
def test_install_rejects_unknown_action(manager: HookManager, bad: str) -> None:
    with pytest.raises(HookError):
        manager.install("user32", "MessageBoxW", bad)


@pytest.mark.parametrize("action", list(HOOK_ACTIONS))
def test_install_accepts_known_actions(manager: HookManager, action: str) -> None:
    info = manager.install("user32", "MessageBoxW", action)
    assert info["action"] == action


@pytest.mark.parametrize("module,function", [("", "MessageBoxW"), ("user32", ""), ("  ", "x")])
def test_install_rejects_empty_names(manager: HookManager, module: str, function: str) -> None:
    with pytest.raises(HookError):
        manager.install(module, function, "log")


def test_unsupported_api_raises_hookerror(manager: HookManager) -> None:
    with pytest.raises(HookError):
        manager.install("gdi32", "NoSuchApi", "log")


# ── CLI arg parsing (patched manager, no native DLL) ─────────────────────────


@pytest.fixture()
def patched_cli(monkeypatch: pytest.MonkeyPatch) -> HookManager:
    """Point ``naturo hook`` at a fake-core-backed manager."""
    import naturo.cli.hook_cmd as hook_cmd

    mgr = HookManager(core=_FakeCore())
    monkeypatch.setattr(hook_cmd, "_manager", lambda: mgr)
    return mgr


def test_cli_install_json(patched_cli: HookManager) -> None:
    import json

    from naturo.cli import main

    result = CliRunner().invoke(main, ["hook", "install", "user32", "MessageBoxW", "-j"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["module"] == "user32.dll"
    assert payload["function"] == "MessageBoxW"
    assert payload["action"] == "log"


def test_cli_install_block_action(patched_cli: HookManager) -> None:
    result = CliRunner().invoke(
        main_cli(), ["hook", "install", "kernel32", "CreateFileW", "--action", "block"]
    )
    assert result.exit_code == 0, result.output
    assert patched_cli.list()[0]["action"] == "block"


def test_cli_install_rejects_bad_action(patched_cli: HookManager) -> None:
    result = CliRunner().invoke(
        main_cli(), ["hook", "install", "user32", "MessageBoxW", "--action", "nope"]
    )
    assert result.exit_code != 0  # click.Choice rejects it at parse time


def test_cli_list_empty(patched_cli: HookManager) -> None:
    result = CliRunner().invoke(main_cli(), ["hook", "list"])
    assert result.exit_code == 0
    assert "No hooks installed" in result.output


def test_cli_list_json_after_install(patched_cli: HookManager) -> None:
    import json

    patched_cli.install("user32", "MessageBoxW", "log")
    result = CliRunner().invoke(main_cli(), ["hook", "list", "-j"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["count"] == 1


def test_cli_remove_json(patched_cli: HookManager) -> None:
    import json

    patched_cli.install("user32", "MessageBoxW", "log")
    result = CliRunner().invoke(main_cli(), ["hook", "remove", "user32", "MessageBoxW", "-j"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["removed"] is True


def test_cli_monitor_json(patched_cli: HookManager) -> None:
    import json

    core: _FakeCore = patched_cli.core  # type: ignore[assignment]
    patched_cli.install("kernel32", "CreateFileW", "log")
    core.simulate_call("kernel32", "CreateFileW", 'path="x"')
    result = CliRunner().invoke(main_cli(), ["hook", "monitor", "-j"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["count"] == 1
    assert payload["events"][0]["detail"] == 'path="x"'


def test_cli_install_hookerror_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    """A HookError from the manager surfaces as a clean INVALID_INPUT envelope."""
    import json

    import naturo.cli.hook_cmd as hook_cmd

    class _Boom:
        def install(self, *a, **k):
            raise HookError("unsupported API")

    monkeypatch.setattr(hook_cmd, "_manager", lambda: _Boom())
    result = CliRunner().invoke(main_cli(), ["hook", "install", "gdi32", "Nope", "-j"])
    assert result.exit_code != 0
    payload = json.loads(result.output)
    assert payload["success"] is False


def main_cli():
    from naturo.cli import main

    return main


# ── Injector: admin pre-flight + argument guards (no real injection) ──────────


@_WINDOWS_ONLY
def test_inject_requires_admin(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    import naturo.hooks.injector as injector

    dll = tmp_path / "fake.dll"
    dll.write_bytes(b"MZ")  # a file that exists; injection never actually runs
    monkeypatch.setattr(injector, "is_admin", lambda: False)

    with pytest.raises(injector.HookInjectionError) as exc:
        injector.inject_dll(4321, str(dll), require_admin=True)
    assert "administrator" in str(exc.value).lower()


@_WINDOWS_ONLY
def test_inject_missing_dll_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import naturo.hooks.injector as injector

    # Even as admin, a missing DLL is rejected before any Win32 call.
    monkeypatch.setattr(injector, "is_admin", lambda: True)
    with pytest.raises(injector.HookInjectionError) as exc:
        injector.inject_dll(4321, "C:/nope/does-not-exist.dll", require_admin=True)
    assert "not found" in str(exc.value).lower()


@_WINDOWS_ONLY
@pytest.mark.parametrize("pid", [0, -1, -999])
def test_inject_invalid_pid_raises(tmp_path, monkeypatch: pytest.MonkeyPatch, pid: int) -> None:
    import naturo.hooks.injector as injector

    dll = tmp_path / "fake.dll"
    dll.write_bytes(b"MZ")
    monkeypatch.setattr(injector, "is_admin", lambda: True)
    with pytest.raises(injector.HookInjectionError):
        injector.inject_dll(pid, str(dll), require_admin=True)


@pytest.mark.skipif(sys.platform == "win32", reason="asserts the non-Windows rejection")
def test_inject_rejects_non_windows(tmp_path) -> None:
    import naturo.hooks.injector as injector

    dll = tmp_path / "fake.dll"
    dll.write_bytes(b"MZ")
    with pytest.raises(injector.HookInjectionError) as exc:
        injector.inject_dll(4321, str(dll), require_admin=True)
    assert "windows" in str(exc.value).lower()


def test_is_admin_returns_bool() -> None:
    from naturo.hooks.injector import is_admin

    assert isinstance(is_admin(), bool)
