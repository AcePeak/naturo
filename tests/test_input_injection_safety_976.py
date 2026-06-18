"""In-process injection-safety assertions and the live-input tripwire (#976).

R-SEC-012 lesson: an unattended QA cycle once typed ``$(rm -rf /)`` into a live
window through a global-``SendInput`` focus race.  The remediation principle is
that *a safety test must never be able to perform the unsafe act it guards
against* — the injection-safety property has to be asserted **in-process**, at
the keystroke-delivery boundary, never by typing shell metacharacters at a real
window.

This module proves two things, both purely in-process (no desktop, no DLL, no
real keystrokes):

1. :func:`naturo.safety.contains_dangerous_input` — the *ungated* matcher that
   classifies content regardless of whether the opt-in runtime guard is enabled
   (the runtime guard, :func:`unsafe_input_reason`, only fires when the QA loop
   has armed it; the tripwire below must detect unconditionally).
2. The session-wide **tripwire** installed by ``conftest`` patches the real
   ``SendInput`` / Phys32 keystroke boundary so any attempt — by any test — to
   live-type shell-metacharacter content raises loudly *before* a single
   keystroke is emitted, while benign text still reaches the real boundary.

The payloads here are deliberately harmless sentinels (``echo INJECTED``); they
still trip every shell-metacharacter pattern but would do nothing if somehow
executed, honouring QA_AGENT.md §7's double-safety rule.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from naturo.safety import contains_dangerous_input, unsafe_input_reason

# Harmless sentinels that still match the shell-metacharacter patterns.
DANGEROUS_SENTINELS = [
    "$(echo INJECTED)",   # command substitution
    "`echo INJECTED`",    # backtick command substitution
    "a && echo INJECTED",  # logical AND
    "a || echo INJECTED",  # logical OR
    "x; echo INJECTED",    # command separator
    "echo INJECTED | cat",  # pipe
    "echo INJECTED > f",   # output redirect
    "cat < f",             # input redirect
]

BENIGN_INPUTS = [
    "QA_PROBE",
    "Hello World",
    "The quick brown fox.",
    "reformatted the document",  # 'format' as a substring, not a command
    "",
]


class TestContainsDangerousInputIsUngated:
    """``contains_dangerous_input`` classifies content independent of the env.

    This is what makes the tripwire reliable: the runtime guard is opt-in, but a
    safety backstop must refuse the unsafe act whether or not the loop armed the
    guard, so it cannot key off ``NATURO_SAFE_INPUT`` / the sentinel file.
    """

    @pytest.mark.parametrize("text", DANGEROUS_SENTINELS)
    def test_detects_dangerous_even_when_guard_disabled(self, text, monkeypatch):
        # Force the opt-in runtime guard OFF regardless of the host machine's
        # state (the real QA machine running this suite may have armed either
        # the env var or the sentinel lock file).
        monkeypatch.setattr("naturo.safety.is_safe_input_enabled", lambda: False)
        # The gated runtime guard is a no-op when disabled ...
        assert unsafe_input_reason(text) is None
        # ... but the ungated matcher still flags the content.
        reason = contains_dangerous_input(text)
        assert reason, f"expected {text!r} to be classified dangerous"
        assert isinstance(reason, str)

    @pytest.mark.parametrize("text", BENIGN_INPUTS)
    def test_benign_passes_ungated(self, text):
        assert contains_dangerous_input(text) is None

    def test_none_is_safe(self):
        assert contains_dangerous_input(None) is None


class TestLiveInputTripwire:
    """The session tripwire refuses unsafe live keystrokes at the SendInput edge.

    A ``MagicMock`` stands in for the native core, so the underlying
    ``key_type`` / ``phys_key_type`` calls are observable and never reach a real
    DLL.  These tests run on every platform (Linux CI included) because no
    desktop or DLL is required.
    """

    def _make_strategy(self, strategy_cls):
        from naturo.backends.windows._strategies import (
            Phys32Strategy,
            SendInputStrategy,
        )

        cls = {"send": SendInputStrategy, "phys": Phys32Strategy}[strategy_cls]
        core = MagicMock()
        return cls(core), core

    @pytest.mark.parametrize("strategy_cls", ["send", "phys"])
    @pytest.mark.parametrize("payload", DANGEROUS_SENTINELS)
    def test_dangerous_live_type_is_refused_with_zero_keystrokes(
        self, strategy_cls, payload
    ):
        strategy, core = self._make_strategy(strategy_cls)
        with pytest.raises(AssertionError, match="R-SEC-012"):
            strategy.type_text(payload)
        # The native keystroke boundary was never reached: zero keystrokes.
        core.key_type.assert_not_called()
        core.phys_key_type.assert_not_called()

    @pytest.mark.parametrize("strategy_cls", ["send", "phys"])
    def test_benign_live_type_passes_through_to_the_core(self, strategy_cls):
        strategy, core = self._make_strategy(strategy_cls)
        strategy.type_text("Hello World")
        if strategy_cls == "send":
            core.key_type.assert_called_once_with("Hello World", 5)
            core.phys_key_type.assert_not_called()
        else:
            core.phys_key_type.assert_called_once_with("Hello World", 5)
            core.key_type.assert_not_called()
