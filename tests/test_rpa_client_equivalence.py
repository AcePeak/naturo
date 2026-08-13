"""Hermetic equivalence tests: rpa-client-* desktop idioms → naturo (#763).

naturo's requirement source is a corpus of ~24 real client RPA repos
(``naturobot-dev/rpa-client-*``). #763 asks us to *prove* — not just document —
that the automation patterns those production scripts use can be reproduced 1:1
with naturo's API surface.

``tests/browser/test_migration_equivalence.py`` (#766) already proves the
*browser* side against real headless-Chrome fixtures, but it is
``@pytest.mark.desktop`` (needs a live Chrome + interactive session) and never
runs on the ``-m "not desktop"`` CI matrix. This module fills the complementary
gap: it proves the **desktop** idiom set — the ``uiautomation`` / ``pywinauto`` /
``pyperclip`` patterns found in repos like ``rpa-client-henjiuyiqian`` (WeChat
Video Channel + Dianping) and the DrissionPage list-scrape shape from
``rpa-client-lingkehudong`` (Xiaohongshu) — entirely **hermetically**.

How: every test drives the real, public :mod:`naturo.sdk` surface against an
injected :class:`FakeUIABackend` that models a tiny in-memory UI and records
every action. No native DLL, no SendInput, no live desktop — so these run
green on every platform in the default deselected suite. Each test pins one
concrete *Before* (old-library) idiom taken verbatim from the corpus to its
naturo *After*, asserting the same semantics: same element matched, same text
extracted, same element count, same keys/clipboard delivered.

Corpus provenance (verified accessible 2026-08, ``gh repo list Naturobot-Dev``):
  * ``rpa-client-henjiuyiqian/winauto视频号_重构版.py`` — uiautomation +
    pywinauto.keyboard.send_keys + pyperclip driving the WeChat client.
  * ``rpa-client-lingkehudong/小红书主页链接_笔记_评论.py`` — pure DrissionPage
    ``page.eles("xpath://...")`` list scrape + ``.text`` extraction.
The client repos are private and NOT vendored here; only the *idiom shapes* are
reproduced, mapped to the naturo equivalent documented in
``docs/MIGRATION_FROM_RPA_SCRIPTS.md``.
"""
from __future__ import annotations

from typing import Any, Optional

import pytest

from naturo import sdk
from naturo.backends.base import CaptureResult, ElementInfo, WindowInfo


# ── in-memory UI model ────────────────────────────────────────────────
def _elem(
    role: str,
    name: str,
    *,
    value: Optional[str] = None,
    x: int = 0,
    y: int = 0,
    w: int = 100,
    h: int = 40,
    writable: bool = False,
    children: Optional[list] = None,
) -> ElementInfo:
    """Build an :class:`ElementInfo` node for the fake tree.

    ``writable`` records whether the control exposes a settable UIA
    ValuePattern (used to steer :func:`naturo.actions.smart_type_text` between
    its value-pattern and clipboard rungs, exactly as a real control would).
    """
    return ElementInfo(
        id=f"{role}:{name}",
        role=role,
        name=name,
        value=value,
        x=x,
        y=y,
        width=w,
        height=h,
        children=children or [],
        properties={"writable": writable},
    )


class FakeUIABackend:
    """A record-only backend modelling one WeChat-like window + a note list.

    Implements only the surface :mod:`naturo.sdk` (and the shared helpers it
    delegates to — ``smart_type_text``/``paste_text``/``wait_for_element``/
    ``require_hwnd``) actually call. Every mutating call is appended to
    :attr:`actions` so a test can assert the exact sequence naturo emitted,
    proving the naturo verb is a faithful stand-in for the old-library idiom.
    """

    HWND = 0xABCD

    def __init__(self, root: ElementInfo) -> None:
        self.root = root
        self.actions: list[tuple[str, Any]] = []
        self.clipboard = ""
        # Toggle to False to force smart_type_text off its value_pattern rung
        # (i.e. simulate a control with no writable ValuePattern → clipboard).
        self.value_pattern_available = True
        # Number of find_element polls to miss before the element "appears"
        # (drives the wait-for-element equivalence test).
        self.find_misses = 0
        self._find_calls = 0

    # ── observe ──────────────────────────────────────────────────────
    def list_windows(self) -> list[WindowInfo]:
        return [
            WindowInfo(
                handle=self.HWND,
                title=self.root.name,
                process_name="WeChat.exe",
                pid=4242,
                x=0,
                y=0,
                width=1200,
                height=800,
                is_visible=True,
                is_minimized=False,
            )
        ]

    def _resolve_hwnd(self, window_title: Optional[str] = None,
                      pid: Optional[int] = None) -> int:
        from naturo.errors import WindowNotFoundError

        if window_title is None or window_title in self.root.name:
            return self.HWND
        raise WindowNotFoundError(f"no window matches {window_title!r}")

    def focus_window(self, title: Optional[str] = None,
                     hwnd: Optional[int] = None) -> None:
        self.actions.append(("focus_window", {"title": title, "hwnd": hwnd}))

    def get_element_tree(self, *, app=None, window_title=None, hwnd=None,
                         pid=None, depth=0, backend="uia") -> ElementInfo:
        self.actions.append(("get_element_tree", {"window_title": window_title}))
        return self.root

    def _walk(self, node: ElementInfo):
        yield node
        for child in node.children or []:
            yield from self._walk(child)

    def find_element(self, selector: Optional[str] = None, *,
                     window_title: Optional[str] = None,
                     hwnd: Optional[int] = None) -> Optional[ElementInfo]:
        self._find_calls += 1
        if self._find_calls <= self.find_misses:
            return None
        role, _, name = (selector or "").partition(":")
        for node in self._walk(self.root):
            if node.role == role and node.name == name:
                return node
        return None

    def get_element_value(self, **kwargs) -> Optional[dict]:
        role, name = kwargs.get("role"), kwargs.get("name")
        for node in self._walk(self.root):
            if node.role == role and node.name == name:
                return {"value": node.value, "role": node.role, "name": node.name}
        return None

    # ── act ──────────────────────────────────────────────────────────
    def click(self, *, x=None, y=None, element_id=None, button="left",
              double=False, input_mode="normal") -> None:
        self.actions.append(
            ("click", {"x": x, "y": y, "button": button, "double": double})
        )

    def set_focused_element_value(self, text: str, append: bool = True) -> bool:
        if self.value_pattern_available:
            self.actions.append(("set_value", {"text": text, "append": append}))
            return True
        return False

    def clipboard_get(self) -> str:
        return self.clipboard

    def clipboard_set(self, text: str) -> None:
        self.clipboard = text
        self.actions.append(("clipboard_set", {"text": text}))

    def hotkey(self, *keys: str, input_mode: str = "normal",
               hold_duration_ms: int = 50) -> None:
        self.actions.append(("hotkey", {"keys": tuple(keys)}))

    def press_key(self, key: str, input_mode: str = "normal") -> None:
        self.actions.append(("press_key", {"key": key}))

    def type_text(self, text: str, **kwargs) -> None:
        self.actions.append(("type_text", {"text": text}))

    def scroll(self, direction="down", amount=3, x=None, y=None) -> None:
        self.actions.append(
            ("scroll", {"direction": direction, "amount": amount})
        )

    def capture_window(self, *, hwnd=None, window_title=None,
                       output_path="capture.png") -> CaptureResult:
        self.actions.append(("capture_window", {"hwnd": hwnd, "path": output_path}))
        return CaptureResult(path=output_path, width=1200, height=800, format="png")

    def capture_screen(self, screen_index: int = 0,
                       output_path: str = "capture.png") -> CaptureResult:
        self.actions.append(("capture_screen", {"path": output_path}))
        return CaptureResult(path=output_path, width=1920, height=1080, format="png")


# ── fixtures: model the WeChat client + a Xiaohongshu note list ───────
def _wechat_tree() -> ElementInfo:
    """A WeChat-shaped window mirroring winauto视频号_重构版.py's control graph."""
    search_edit = _elem("Edit", "", x=200, y=60, w=300, h=30, writable=True)
    video_tab = _elem("Text", "视频号", x=20, y=120, w=80, h=30)
    latest_btn = _elem("Text", "最新", x=400, y=120, w=60, h=30)
    more_btn = _elem("Button", "更多功能", x=1100, y=20, w=40, h=40)
    panel = _elem(
        "Pane", "Chrome_WidgetWin_0", x=0, y=100, w=1200, h=700,
        children=[video_tab, latest_btn, search_edit],
    )
    return _elem(
        "Window", "微信", x=0, y=0, w=1200, h=800,
        children=[more_btn, panel],
    )


def _note_list_tree() -> ElementInfo:
    """A Xiaohongshu explore-feed shape: N note items each carrying a title.

    Mirrors ``page.eles("xpath://div[contains(@class,'note-item')]")`` +
    ``item.ele('...').text`` from rpa-client-lingkehudong.
    """
    titles = ["穿搭分享", "美食探店", "旅行日记", "护肤心得", "健身打卡"]
    items = [
        _elem("Group", "note-item", children=[_elem("Text", t, value=t)])
        for t in titles
    ]
    return _elem("Document", "explore-feed", children=items)


@pytest.fixture
def wechat() -> tuple[sdk.Desktop, FakeUIABackend]:
    backend = FakeUIABackend(_wechat_tree())
    return sdk.Desktop(backend=backend), backend


@pytest.fixture
def notes() -> tuple[sdk.Desktop, FakeUIABackend]:
    backend = FakeUIABackend(_note_list_tree())
    return sdk.Desktop(backend=backend), backend


# ══════════════════════════════════════════════════════════════════════
# Pattern 1 — Window finding
#   Before (uiautomation): auto.WindowControl(searchDepth=1, Name="微信")
#   After  (naturo):       naturo.see(window="微信")  /  require_hwnd focus
# ══════════════════════════════════════════════════════════════════════
class TestWindowFinding:
    def test_see_matches_named_window(self, wechat):
        desktop, _ = wechat
        root = desktop.see(window="微信")
        assert root is not None
        assert root.role == "Window"
        assert root.name == "微信"

    def test_named_but_absent_window_fails_loudly(self, wechat):
        """A supplied-but-unresolvable selector must raise, not act on foreground.

        uiautomation silently returns a non-existent control (``.Exists()`` is
        False); naturo instead fails loudly — the safer contract (#957/#1291).
        """
        from naturo.errors import WindowNotFoundError

        desktop, _ = wechat
        with pytest.raises(WindowNotFoundError):
            desktop.click(x=1, y=1, window="钉钉")

    def test_focus_resolves_named_window(self, wechat):
        desktop, backend = wechat
        desktop.click(x=5, y=5, window="微信")
        assert ("focus_window", {"title": "微信", "hwnd": backend.HWND}) \
            in backend.actions


# ══════════════════════════════════════════════════════════════════════
# Pattern 2 — Find by control-type + name, then click
#   Before: wechat.ButtonControl(Name="更多功能").Click()
#   After:  naturo.find("Button:更多功能").click()
# ══════════════════════════════════════════════════════════════════════
class TestFindAndClick:
    def test_find_by_role_and_name(self, wechat):
        desktop, backend = wechat
        backend.find_element = lambda *a, **k: _walk_find(backend.root, "Button", "更多功能")  # noqa: E731
        el = desktop.find("Button:更多功能")
        assert el is not None and el.role == "Button" and el.name == "更多功能"

    def test_click_targets_element_center(self, wechat):
        desktop, backend = wechat
        # find the tab via the live-backend find, then click it
        el = desktop.find("Text:视频号")
        assert el is not None
        el.click()
        # 视频号 tab is at x=20,y=120,w=80,h=30 → centre (60,135)
        assert ("click", {"x": 60, "y": 135, "button": "left", "double": False}) \
            in backend.actions

    def test_in_memory_subtree_find(self, wechat):
        """item.ele('...') style: search an already-fetched subtree, no re-query."""
        desktop, backend = wechat
        root = desktop.see(window="微信")
        tab = root.find("Text:视频号")
        assert tab is not None and tab.name == "视频号"
        # a pure in-memory walk — only the tree fetch hit the backend
        assert [a[0] for a in backend.actions] == ["get_element_tree"]


def _walk_find(node, role, name):
    if node.role == role and node.name == name:
        return node
    for c in node.children or []:
        found = _walk_find(c, role, name)
        if found:
            return found
    return None


# ══════════════════════════════════════════════════════════════════════
# Pattern 3 — Text extraction
#   Before (DrissionPage): page.ele(sel).text   /   .attr('href')
#   After  (naturo):       Element.value  /  Desktop.get_value(...)
# ══════════════════════════════════════════════════════════════════════
class TestTextExtraction:
    def test_element_value_matches_text(self, notes):
        desktop, _ = notes
        root = desktop.see()
        first_title = next(
            d for d in root.descendants() if d.role == "Text"
        )
        assert first_title.value == "穿搭分享"

    def test_get_value_reads_named_element(self, notes):
        desktop, backend = notes
        val = desktop.get_value(role="Text", name="美食探店")
        assert val == {"value": "美食探店", "role": "Text", "name": "美食探店"}


# ══════════════════════════════════════════════════════════════════════
# Pattern 4 — List / table scrape (the Phase-1 #763 criterion)
#   Before: items = page.eles("xpath://div[contains(@class,'note-item')]")
#           for it in items: title = it.ele('.//span').text
#   After:  root.descendants() filtered by role  → same count, same text
# ══════════════════════════════════════════════════════════════════════
class TestListScrape:
    def test_same_element_count(self, notes):
        desktop, _ = notes
        root = desktop.see()
        note_items = [d for d in root.descendants() if d.name == "note-item"]
        assert len(note_items) == 5  # same N DrissionPage's eles() returns

    def test_same_text_content_in_order(self, notes):
        desktop, _ = notes
        root = desktop.see()
        titles = [
            item.find("Text:*").value
            for item in root.descendants()
            if item.name == "note-item"
        ]
        assert titles == [
            "穿搭分享", "美食探店", "旅行日记", "护肤心得", "健身打卡",
        ]


# ══════════════════════════════════════════════════════════════════════
# Pattern 5 — Keyboard idioms (pywinauto.keyboard.send_keys)
#   Before: send_keys('^a') / send_keys('{ENTER}') / send_keys('{PGDN}')
#   After:  naturo hotkey ctrl+a / press enter / press pagedown
# ══════════════════════════════════════════════════════════════════════
class TestKeyboard:
    def test_hotkey_combo(self, wechat):
        desktop, backend = wechat
        desktop.press("ctrl+a")           # ^a
        assert ("hotkey", {"keys": ("ctrl", "a")}) in backend.actions

    def test_single_key_press(self, wechat):
        desktop, backend = wechat
        desktop.press("enter")            # {ENTER}
        desktop.press("pagedown")         # {PGDN}
        keys = [a[1]["key"] for a in backend.actions if a[0] == "press_key"]
        assert keys == ["enter", "pagedown"]

    def test_press_repeat_count(self, wechat):
        """send_keys('{PGDN}' * 3) → press('pagedown', count=3)."""
        desktop, backend = wechat
        desktop.press("pagedown", count=3)
        assert sum(1 for a in backend.actions if a[0] == "press_key") == 3


# ══════════════════════════════════════════════════════════════════════
# Pattern 6 — Chinese text entry (pyperclip.copy + send_keys('^v'))
#   Before: pyperclip.copy(kw); send_keys('^a'); send_keys('^v')
#   After:  Element.type(kw) — the IME-immune ladder (value_pattern→clipboard)
# ══════════════════════════════════════════════════════════════════════
class TestChineseInput:
    def test_value_pattern_rung_when_writable(self, wechat):
        """A writable control takes the instant ValuePattern rung (no keystrokes)."""
        desktop, backend = wechat
        edit = desktop.find("Edit:")
        assert edit is not None
        method = edit.type("大众点评")
        assert method == "value_pattern"
        assert ("set_value", {"text": "大众点评", "append": True}) in backend.actions

    def test_clipboard_paste_rung_reproduces_pyperclip_idiom(self, wechat):
        """No ValuePattern → clipboard + Ctrl+V, exactly the old pyperclip flow.

        This is the faithful reproduction of ``pyperclip.copy(kw); send_keys('^v')``:
        the clipboard is set to the keyword and a Ctrl+V hotkey is delivered.
        """
        desktop, backend = wechat
        backend.value_pattern_available = False
        method = desktop.type("很久以前", window="微信")
        assert method == "clipboard_paste"
        assert ("clipboard_set", {"text": "很久以前"}) in backend.actions
        assert ("hotkey", {"keys": ("ctrl", "v")}) in backend.actions


# ══════════════════════════════════════════════════════════════════════
# Pattern 7 — Implicit wait-for-element
#   Before (DrissionPage): page.ele(sel, timeout=10)  (implicit retry-until)
#   After  (naturo):       naturo.wait("Role:Name", timeout=...)
# ══════════════════════════════════════════════════════════════════════
class TestWait:
    def test_wait_polls_until_present(self, wechat):
        desktop, backend = wechat
        backend.find_misses = 2  # miss twice, then resolve
        res = desktop.wait("Text:视频号", timeout=2.0, poll_interval=0.01)
        assert res.found is True
        assert res.element is not None and res.element.name == "视频号"

    def test_wait_times_out_when_absent(self, wechat):
        desktop, _ = wechat
        res = desktop.wait("Button:不存在", timeout=0.05, poll_interval=0.01)
        assert res.found is False


# ══════════════════════════════════════════════════════════════════════
# Pattern 8 — Scroll (infinite-scroll scrape) & Screenshot
#   Before: page.scroll.down(1000) / send_keys('{PGDN}') ; page.get_screenshot()
#   After:  Desktop.scroll(direction="down") ; Desktop.capture(path, window=...)
# ══════════════════════════════════════════════════════════════════════
class TestScrollAndCapture:
    def test_scroll_down(self, wechat):
        desktop, backend = wechat
        desktop.scroll(direction="down", amount=10)
        assert ("scroll", {"direction": "down", "amount": 10}) in backend.actions

    def test_capture_window(self, wechat, tmp_path):
        desktop, backend = wechat
        out = str(tmp_path / "wechat.png")
        result = desktop.capture(out, window="微信")
        assert isinstance(result, CaptureResult)
        assert result.path == out
        assert any(
            a[0] == "capture_window" and a[1]["hwnd"] == backend.HWND
            for a in backend.actions
        )
