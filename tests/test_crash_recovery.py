"""M4 criterion 2 — generalized crash-recovery / self-heal for the native core.

The comtypes gen-cache self-heal (#1220) recovered a broken UIA codegen cache on
the next call. This generalizes the same idea to the native recognition/input
layers: if the cached ``NaturoCore``/COM instance goes bad mid-session,
``heal_core_on_failure`` resets it so the next call re-initializes rather than
staying broken forever, logging a WARNING.

These tests exercise the decorator + ``CoreMixin`` reset logic directly on a fake
core — no ``WindowsBackend`` instantiation (that needs Win32), so the module is
Linux-collectable.
"""
from __future__ import annotations

import logging

import pytest

from naturo.backends.windows._core import CoreMixin, heal_core_on_failure
from naturo.bridge import NaturoCoreError


class _FakeCore:
    """Stand-in for the native core: raises a COM error (-2) when ``broken``."""

    def __init__(self, broken: bool):
        self.broken = broken
        self.op_calls = 0

    def do_op(self, value):
        self.op_calls += 1
        if self.broken:
            raise NaturoCoreError(-2, "do_op")  # -2 == System/COM error (recoverable)
        return f"ok:{value}"

    def do_op_fatal(self, value):
        raise NaturoCoreError(-1, "do_op")  # -1 == invalid argument (NOT recoverable)


class _FakeBackend:
    """Minimal object with the CoreMixin self-heal surface + a lazy fake core.

    The first core built is ``broken`` (raises -2); every core built after a
    reset is healthy — modelling a COM instance that went bad then re-initialized.
    """

    _reset_core = CoreMixin._reset_core
    _is_recoverable_core_failure = staticmethod(CoreMixin._is_recoverable_core_failure)

    def __init__(self):
        self._core = None
        self._initialized = False
        self.core_builds = 0

    def _ensure_core(self) -> _FakeCore:
        if self._core is None:
            self.core_builds += 1
            self._core = _FakeCore(broken=(self.core_builds == 1))
            self._initialized = True
        return self._core

    @heal_core_on_failure(retry=True)
    def recognize(self, value):
        """Idempotent (recognition-like) — self-heals within the same call."""
        return self._ensure_core().do_op(value)

    @heal_core_on_failure(retry=False)
    def act(self, value):
        """Side-effecting (input-like) — resets on failure, heals on next call."""
        return self._ensure_core().do_op(value)

    @heal_core_on_failure(retry=True)
    def recognize_fatal(self, value):
        return self._ensure_core().do_op_fatal(value)


def test_idempotent_op_self_heals_in_place(caplog):
    """retry=True: a broken core is reset + re-initialized and the SAME call
    succeeds — the generalized #1220 self-heal (M4-2)."""
    be = _FakeBackend()
    with caplog.at_level(logging.WARNING):
        result = be.recognize("x")
    assert result == "ok:x"            # the call succeeded despite the first core failing
    assert be.core_builds == 2         # core was rebuilt (re-initialized) once
    assert any("self-heal" in r.message and "recognize" in r.message for r in caplog.records), \
        "expected a WARNING documenting the self-heal"


def test_side_effecting_op_resets_then_next_call_succeeds(caplog):
    """retry=False: the failing input call propagates (no double-act), the core
    is reset, and the NEXT call re-initializes and succeeds."""
    be = _FakeBackend()
    with caplog.at_level(logging.WARNING):
        with pytest.raises(NaturoCoreError):
            be.act("a")                # first call fails (broken core) ...
        assert be._core is None        # ... but the core was reset (will re-init)
        result = be.act("b")           # the NEXT call self-heals
    assert result == "ok:b"
    assert be.core_builds == 2
    assert any("self-heal" in r.message for r in caplog.records)


def test_non_recoverable_error_is_not_healed_or_retried(caplog):
    """A non-COM op fault (code -1) must NOT reset/retry the core — a genuine bad
    request surfaces immediately, no infinite-heal, core untouched."""
    be = _FakeBackend()
    with caplog.at_level(logging.WARNING):
        with pytest.raises(NaturoCoreError) as ei:
            be.recognize_fatal("x")
    assert ei.value.code == -1
    assert be.core_builds == 1                      # core was NOT rebuilt
    assert be._core is not None                     # core was NOT reset
    assert not any("self-heal" in r.message for r in caplog.records)


def test_reset_core_clears_cached_instance():
    """_reset_core drops the cached core so _ensure_core rebuilds it."""
    be = _FakeBackend()
    first = be._ensure_core()
    assert be._core is first and be._initialized is True
    be._reset_core()
    assert be._core is None and be._initialized is False
    second = be._ensure_core()
    assert second is not first                       # a fresh core after reset
