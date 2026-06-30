from __future__ import annotations

import os
from typing import Optional
from unittest.mock import MagicMock

import pytest


# ── CI Windows guard ─────────────────────────────
# GitHub Actions windows-latest has NO desktop session.
# Any test that instantiates WindowsBackend() or NaturoCore() will hang
# because UIA/COM initialization blocks without a desktop.
# Instead of relying on individual test authors to add @pytest.mark.desktop,
# we monkeypatch the constructors to auto-skip on CI Windows.

_ON_CI = os.environ.get("CI") == "true"
_IS_WINDOWS = os.name == "nt"
_CI_WINDOWS = _ON_CI and _IS_WINDOWS

if _CI_WINDOWS:
    import naturo.backends.windows as _win_mod
    import naturo.bridge as _bridge_mod

    _OrigWindowsBackend = _win_mod.WindowsBackend
    _OrigNaturoCore = _bridge_mod.NaturoCore

    class _SkippingWindowsBackend(_OrigWindowsBackend):
        def __init__(self, *args, **kwargs):
            pytest.skip(
                "WindowsBackend() skipped on CI Windows (no desktop session). "
                "Add @pytest.mark.desktop if this test requires a real desktop.",
                allow_module_level=True,
            )

    class _SkippingNaturoCore:
        def __init__(self, *args, **kwargs):
            import threading
            if threading.current_thread() is not threading.main_thread():
                # (#683) pytest.skip() fails in daemon threads (no pytest
                # request context).  The detection chain runs probes in
                # daemon threads, so raise a regular exception instead —
                # the probe's exception handler logs and returns None.
                raise RuntimeError(
                    "NaturoCore() blocked on CI Windows (no desktop session, "
                    "daemon thread context)"
                )
            pytest.skip(
                "NaturoCore() skipped on CI Windows (no desktop session). "
                "Add @pytest.mark.desktop if this test requires a real desktop.",
                allow_module_level=True,
            )

    _win_mod.WindowsBackend = _SkippingWindowsBackend  # type: ignore[misc]
    _bridge_mod.NaturoCore = _SkippingNaturoCore  # type: ignore[misc]


def pytest_configure(config):
    """Register custom markers."""
    pass  # markers defined in pyproject.toml


def _has_desktop_session() -> bool:
    """Check if an interactive desktop session is available.

    On Windows, queries the WTS (Windows Terminal Services) API to determine
    whether the current process runs in an active Console or RDP session.
    This correctly returns False for SSH sessions, unlike the old
    ``GetDesktopWindow()`` approach which returned True for any session type.

    Uses the same detection logic as ``naturo.cli.interaction._is_current_session_interactive()``.

    Always returns False on non-Windows platforms.
    """
    if os.name != "nt":
        return False
    try:
        import ctypes
        import ctypes.wintypes

        # Get the session ID for the current process.
        pid = ctypes.windll.kernel32.GetCurrentProcessId()
        session_id = ctypes.wintypes.DWORD(0)
        ok = ctypes.windll.kernel32.ProcessIdToSessionId(
            pid, ctypes.byref(session_id),
        )
        if not ok:
            return False
        sid = session_id.value

        # Session 0 is always the non-interactive services session.
        if sid == 0:
            return False

        # Query WTS connect state via pure ctypes.
        WTS_CURRENT_SERVER_HANDLE = 0
        WTSConnectState = 8  # WTS_INFO_CLASS enum value
        WTSActive = 0
        WTSConnected = 1

        wtsapi32 = ctypes.windll.wtsapi32
        buf = ctypes.wintypes.LPWSTR()
        bytes_returned = ctypes.wintypes.DWORD(0)

        ok = wtsapi32.WTSQuerySessionInformationW(
            WTS_CURRENT_SERVER_HANDLE,
            sid,
            WTSConnectState,
            ctypes.byref(buf),
            ctypes.byref(bytes_returned),
        )
        if not ok:
            return False

        try:
            state = ctypes.cast(
                buf, ctypes.POINTER(ctypes.wintypes.DWORD),
            ).contents.value
        finally:
            wtsapi32.WTSFreeMemory(buf)

        return state in (WTSActive, WTSConnected)
    except Exception:
        return False


# Cache the result once per session to avoid repeated FFI calls.
_DESKTOP_AVAILABLE: Optional[bool] = None


def _check_desktop() -> bool:
    """Return cached desktop session availability."""
    global _DESKTOP_AVAILABLE
    if _DESKTOP_AVAILABLE is None:
        _DESKTOP_AVAILABLE = _has_desktop_session()
    return _DESKTOP_AVAILABLE


@pytest.fixture(autouse=True)
def _skip_desktop_tests(request: pytest.FixtureRequest):
    """Auto-skip tests marked ``@pytest.mark.desktop`` when no desktop session.

    This covers the gap where tests guard on ``platform.system() == 'Windows'``
    but still fail when run via SSH (Windows, but no interactive desktop).
    """
    if request.node.get_closest_marker("desktop") is not None:
        if not _check_desktop():
            pytest.skip("No interactive desktop session available")


@pytest.fixture(autouse=True, scope="session")
def _forbid_unsafe_live_input():
    """Structural backstop: no test may live-type shell metacharacters (#976).

    R-SEC-012: an unattended QA cycle once typed ``$(rm -rf /)`` into a live
    window through a global-``SendInput`` focus race.  The lesson is that a
    safety test must never be able to perform the unsafe act it guards against —
    the injection-safety property must be asserted in-process, never by putting
    shell metacharacters on a real keyboard.

    This session-wide tripwire patches the real keystroke-delivery boundary (the
    ``SendInput`` and Phys32 input strategies) so that any attempt — by any test,
    intentional or accidental — to type a string containing shell-command
    content raises loudly *before* a single keystroke is emitted.  Benign text
    still reaches the original implementation, so legitimate desktop ``type``
    tests are unaffected.  Detection is ungated (it does not depend on the opt-in
    ``NATURO_SAFE_INPUT`` runtime guard) so the backstop holds in every run.
    """
    from naturo.backends.windows import _strategies
    from naturo.safety import contains_dangerous_input

    originals: dict[type, object] = {}

    def _make_guarded(original):
        def guarded(self, text, delay_ms=5):
            reason = contains_dangerous_input(text)
            if reason is not None:
                raise AssertionError(
                    "R-SEC-012 tripwire: refusing to live-type shell-unsafe "
                    f"content ({reason}) via {type(self).__name__}.type_text. "
                    "Injection-safety must be asserted in-process (see "
                    "tests/test_input_injection_safety_976.py), never through "
                    f"real keystrokes. Payload repr: {text!r}"
                )
            return original(self, text, delay_ms)

        return guarded

    for strategy_cls in (_strategies.SendInputStrategy, _strategies.Phys32Strategy):
        originals[strategy_cls] = strategy_cls.type_text
        strategy_cls.type_text = _make_guarded(strategy_cls.type_text)  # type: ignore[method-assign]

    try:
        yield
    finally:
        for strategy_cls, original in originals.items():
            strategy_cls.type_text = original  # type: ignore[method-assign]


def cli_stdout(result):
    """Extract stdout-only text from a Click CliRunner result.

    Click 8.x's ``result.output`` mixes stderr and stdout. Use
    ``result.stdout`` when available (Click ≥8.0) to avoid stderr
    warnings contaminating JSON output assertions.
    """
    return getattr(result, "stdout", result.output)


@pytest.fixture
def is_windows():
    return os.name == "nt"


@pytest.fixture
def skip_if_not_windows():
    if os.name != "nt":
        pytest.skip("Windows-only test")
