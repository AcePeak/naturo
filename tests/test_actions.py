"""Unit tests for the shared action layer (naturo/actions.py).

These lock in the reliability-ladder ordering that both the CLI `type` and the
MCP `type_text` now share, so the two surfaces cannot drift back to the bug
this module fixed: the MCP path used to paste (Ctrl+V) *before* keystroke and
without verifying, so it silently "succeeded" on CEF controls (DingTalk) that
drop a synthetic paste.

No real input is sent — a fake backend records calls.
"""
from __future__ import annotations

import types

from naturo import actions


class FakeBackend:
    """Records which rung of the ladder was exercised."""

    def __init__(self, vp_ok: bool = False):
        self.vp_ok = vp_ok
        self.calls: list[tuple] = []

    def set_focused_element_value(self, text, append=False):
        self.calls.append(("value_pattern", text))
        return self.vp_ok

    def type_text(self, text, wpm=120, input_mode="normal", profile="linear"):
        self.calls.append(("keystroke", text, profile))

    def clipboard_get(self):
        return ""

    def clipboard_set(self, text):
        self.calls.append(("clipboard_set", text))

    def hotkey(self, *keys, **_kw):
        self.calls.append(("hotkey", keys))

    def press_key(self, key, input_mode="normal"):
        self.calls.append(("press_key", key))

    def kinds(self):
        return [c[0] for c in self.calls]


def test_value_pattern_wins_and_skips_keystroke():
    b = FakeBackend(vp_ok=True)
    out = actions.smart_type_text(b, "hi")
    assert out["method"] == "value_pattern"
    assert out["verified"] is True
    assert "keystroke" not in b.kinds()
    assert "hotkey" not in b.kinds()  # no paste


def test_keystroke_used_on_cef_no_paste(monkeypatch):
    # CEF: no ValuePattern, and the value can't be read back → verify UNKNOWN.
    monkeypatch.setattr("naturo.verify.capture_before_state", lambda *a, **k: {})
    monkeypatch.setattr(
        "naturo.verify.verify_type",
        lambda *a, **k: types.SimpleNamespace(verified=None),
    )
    b = FakeBackend(vp_ok=False)
    out = actions.smart_type_text(b, "你好")
    assert out["method"] == "keystroke"
    assert out["verified"] is None
    # keystroke ran with the human profile; paste must NOT pre-empt it.
    assert ("keystroke", "你好", "human") in b.calls
    assert "hotkey" not in b.kinds()


def test_paste_fallback_only_on_verified_keystroke_failure(monkeypatch):
    monkeypatch.setattr(
        "naturo.verify.capture_before_state", lambda *a, **k: {"value": "before"}
    )
    seq = iter([False, True])  # keystroke verify fails, paste verify passes

    def fake_verify(*a, **k):
        return types.SimpleNamespace(verified=next(seq))

    monkeypatch.setattr("naturo.verify.verify_type", fake_verify)
    b = FakeBackend(vp_ok=False)
    out = actions.smart_type_text(b, "hello")
    assert out["method"] == "clipboard_paste"
    assert out["verified"] is True
    # keystroke was tried first, THEN paste as the verified fallback.
    assert b.kinds().index("keystroke") < b.kinds().index("hotkey")


def test_verify_off_skips_reads_and_stays_keystroke():
    b = FakeBackend(vp_ok=False)
    out = actions.smart_type_text(b, "abc", verify=False)
    assert out["method"] == "keystroke"
    assert out["verified"] is None
    assert "hotkey" not in b.kinds()


def test_press_combo_routes_through_hotkey():
    b = FakeBackend()
    out = actions.smart_press_key(b, "ctrl+c")
    assert out == {"method": "hotkey", "combo": "ctrl+c"}
    assert b.calls == [("hotkey", ("ctrl", "c"))]


def test_press_standalone_modifier_routes_through_hotkey():
    # The bug: MCP used to send a lone `alt` to press_key (a no-op). It must hotkey.
    b = FakeBackend()
    out = actions.smart_press_key(b, "alt")
    assert out["method"] == "hotkey"
    assert out["combo"] is None
    assert b.calls == [("hotkey", ("alt",))]
    assert "press_key" not in b.kinds()


def test_press_regular_key_uses_press_key():
    b = FakeBackend()
    out = actions.smart_press_key(b, "enter", count=2)
    assert out["method"] == "key"
    assert b.calls == [("press_key", "enter"), ("press_key", "enter")]


def test_press_modifier_alias_normalizes():
    b = FakeBackend()
    actions.smart_press_key(b, "control")  # alias of ctrl
    assert b.calls == [("hotkey", ("ctrl",))]
