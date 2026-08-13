"""Hermetic tests for the in-process Python SDK (#924).

Every test mocks the backend (and, where relevant, the shared helpers the SDK
delegates to), so no live desktop is touched. The point is to prove each verb
forwards to the RIGHT backend/actions call with the RIGHT args and returns a
sensible object — i.e. that the SDK is a faithful thin wrapper, not a fork.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import naturo
from naturo import sdk
from naturo.backends.base import CaptureResult, ElementInfo


# ── fixtures ──────────────────────────────────────────────────────────
def _elem(role="Button", name="Save", value=None, x=10, y=20, w=100, h=40,
          children=None) -> ElementInfo:
    return ElementInfo(
        id=f"{role}:{name}", role=role, name=name, value=value,
        x=x, y=y, width=w, height=h,
        children=children or [], properties={},
    )


@pytest.fixture
def backend() -> MagicMock:
    return MagicMock(name="backend")


@pytest.fixture
def desktop(backend) -> sdk.Desktop:
    return sdk.Desktop(backend=backend)


# ── Desktop.backend resolution ────────────────────────────────────────
class TestBackendResolution:
    def test_explicit_backend_used(self, backend):
        d = sdk.Desktop(backend=backend)
        assert d.backend is backend

    def test_lazy_backend_autodetected(self):
        fake = MagicMock()
        with patch("naturo.sdk.get_backend", return_value=fake) as gb:
            d = sdk.Desktop()
            assert d.backend is fake
            # cached — resolved once
            assert d.backend is fake
            gb.assert_called_once()


# ── observe: windows / see / find ─────────────────────────────────────
class TestObserve:
    def test_windows_delegates_to_list_windows(self, desktop, backend):
        backend.list_windows.return_value = ["w1", "w2"]
        assert desktop.windows() == ["w1", "w2"]
        backend.list_windows.assert_called_once_with()

    def test_monitors_delegates(self, desktop, backend):
        backend.list_monitors.return_value = ["m0"]
        assert desktop.monitors() == ["m0"]
        backend.list_monitors.assert_called_once_with()

    def test_see_calls_get_element_tree_with_args(self, desktop, backend):
        root = _elem(role="Window", name="Notepad")
        backend.get_element_tree.return_value = root
        el = desktop.see(window="Notepad", depth=3)
        assert isinstance(el, sdk.Element)
        assert el.info is root
        backend.get_element_tree.assert_called_once_with(
            app=None, window_title="Notepad", hwnd=None, pid=None,
            depth=3, backend="uia",
        )

    def test_see_returns_none_when_no_window(self, desktop, backend):
        backend.get_element_tree.return_value = None
        assert desktop.see(window="Ghost") is None

    def test_see_cascade_uses_run_cascade(self, desktop, backend):
        root = _elem(role="Window", name="Chrome")
        fake_result = MagicMock(tree=root)
        with patch("naturo.cascade.run_cascade", return_value=fake_result) as rc:
            el = desktop.see(app="chrome", cascade=True)
        assert isinstance(el, sdk.Element)
        assert el.info is root
        rc.assert_called_once()
        _, kwargs = rc.call_args
        assert kwargs["app"] == "chrome"
        assert kwargs["backend_name"] == "auto"

    def test_find_returns_element(self, desktop, backend):
        backend.find_element.return_value = _elem()
        el = desktop.find("Button:Save", window="Notepad")
        assert isinstance(el, sdk.Element)
        backend.find_element.assert_called_once_with(
            selector="Button:Save", window_title="Notepad", hwnd=None,
        )

    def test_find_returns_none(self, desktop, backend):
        backend.find_element.return_value = None
        assert desktop.find("Button:Nope") is None


# ── Element wrapper ───────────────────────────────────────────────────
class TestElement:
    def test_properties(self, desktop):
        el = sdk.Element(_elem(role="Edit", name="Body", value="hi"), desktop)
        assert el.role == "Edit"
        assert el.name == "Body"
        assert el.value == "hi"
        assert el.id == "Edit:Body"
        assert el.bounds == (10, 20, 100, 40)

    def test_center(self, desktop):
        el = sdk.Element(_elem(x=0, y=0, w=100, h=40), desktop)
        assert el.center == (50, 20)

    def test_children_and_descendants(self, desktop):
        leaf = _elem(role="Text", name="leaf")
        mid = _elem(role="Group", name="mid", children=[leaf])
        root = _elem(role="Window", name="root", children=[mid])
        rel = sdk.Element(root, desktop)
        assert [c.name for c in rel.children] == ["mid"]
        assert sorted(d.name for d in rel.descendants()) == ["leaf", "mid"]

    def test_find_in_subtree(self, desktop):
        save = _elem(role="Button", name="Save")
        root = _elem(role="Window", name="root", children=[save])
        rel = sdk.Element(root, desktop)
        found = rel.find("Button:Save")
        assert found is not None and found.name == "Save"
        assert rel.find("Button:Missing") is None

    def test_click_uses_center(self, desktop, backend):
        el = sdk.Element(_elem(x=0, y=0, w=100, h=40), desktop)
        ret = el.click()
        assert ret is el  # chainable
        backend.click.assert_called_once_with(
            x=50, y=20, button="left", double=False, input_mode="normal",
        )

    def test_type_focuses_then_types(self, desktop, backend):
        el = sdk.Element(_elem(x=0, y=0, w=100, h=40), desktop)
        with patch("naturo.sdk.smart_type_text", return_value="value_pattern") as stt:
            method = el.type("hello", wpm=90)
        assert method == "value_pattern"
        backend.click.assert_called_once()  # focused first
        stt.assert_called_once_with(backend, "hello", input_mode="normal", wpm=90)

    def test_get_value_delegates(self, desktop, backend):
        backend.get_element_value.return_value = {"value": "x"}
        el = sdk.Element(_elem(role="Edit", name="Body"), desktop)
        assert el.get_value() == {"value": "x"}
        backend.get_element_value.assert_called_once_with(role="Edit", name="Body")

    def test_set_value_delegates(self, desktop, backend):
        backend.set_element_value.return_value = True
        el = sdk.Element(_elem(role="Edit", name="Body"), desktop)
        assert el.set_value("new") is True
        backend.set_element_value.assert_called_once_with(
            text="new", role="Edit", name="Body",
        )


# ── act: click / type / press ─────────────────────────────────────────
class TestActions:
    def test_click_coords(self, desktop, backend):
        desktop.click(x=5, y=6)
        backend.click.assert_called_once_with(
            x=5, y=6, element_id=None, button="left", double=False,
            input_mode="normal",
        )

    def test_click_focuses_window(self, desktop, backend):
        backend._resolve_hwnd.return_value = 4242
        desktop.click(x=5, y=6, window="Notepad")
        backend.focus_window.assert_called_once_with(hwnd=4242, title="Notepad")

    def test_type_routes_through_ladder(self, desktop, backend):
        with patch("naturo.sdk.smart_type_text", return_value="clipboard_paste") as stt:
            method = desktop.type("hi", wpm=200)
        assert method == "clipboard_paste"
        stt.assert_called_once_with(backend, "hi", input_mode="normal", wpm=200)

    def test_type_focuses_target_window(self, desktop, backend):
        backend._resolve_hwnd.return_value = 77
        with patch("naturo.sdk.smart_type_text", return_value="keystroke"):
            desktop.type("hi", window="Notepad")
        backend.focus_window.assert_called_once_with(hwnd=77, title="Notepad")

    def test_press_single_key(self, desktop, backend):
        desktop.press("enter")
        backend.press_key.assert_called_once_with(key="enter", input_mode="normal")

    def test_press_combo_uses_hotkey(self, desktop, backend):
        desktop.press("ctrl+s")
        backend.hotkey.assert_called_once_with("ctrl", "s", input_mode="normal")

    def test_press_count(self, desktop, backend):
        desktop.press("tab", count=3)
        assert backend.press_key.call_count == 3

    def test_hotkey_delegates(self, desktop, backend):
        desktop.hotkey("ctrl", "c")
        backend.hotkey.assert_called_once_with("ctrl", "c", input_mode="normal")

    def test_scroll_delegates(self, desktop, backend):
        desktop.scroll(direction="up", amount=5)
        backend.scroll.assert_called_once_with(
            direction="up", amount=5, x=None, y=None,
        )


# ── values ────────────────────────────────────────────────────────────
class TestValues:
    def test_get_value(self, desktop, backend):
        backend.get_element_value.return_value = {"value": "42"}
        out = desktop.get_value(ref="e5")
        assert out == {"value": "42"}
        backend.get_element_value.assert_called_once_with(
            ref="e5", automation_id=None, role=None, name=None,
            window_title=None, hwnd=None,
        )

    def test_set_value_resolves_then_sets(self, desktop, backend):
        backend._resolve_hwnd.return_value = 999
        backend.set_element_value.return_value = True
        assert desktop.set_value("hi", role="Edit", window="Notepad") is True
        backend.set_element_value.assert_called_once_with(
            text="hi", hwnd=999, automation_id=None, role="Edit", name=None,
        )


# ── capture ───────────────────────────────────────────────────────────
class TestCapture:
    def _result(self):
        return CaptureResult(path="out.png", width=800, height=600, format="png")

    def test_capture_screen_default(self, desktop, backend):
        backend.capture_screen.return_value = self._result()
        res = desktop.capture("out.png")
        assert res.path == "out.png"
        backend.capture_screen.assert_called_once_with(
            screen_index=0, output_path="out.png",
        )

    def test_capture_screen_index(self, desktop, backend):
        backend.capture_screen.return_value = self._result()
        desktop.capture("out.png", screen=1)
        backend.capture_screen.assert_called_once_with(
            screen_index=1, output_path="out.png",
        )

    def test_capture_window_by_hwnd(self, desktop, backend):
        backend.capture_window.return_value = self._result()
        desktop.capture("w.png", hwnd=123)
        backend.capture_window.assert_called_once_with(hwnd=123, output_path="w.png")

    def test_capture_window_by_title_resolves_hwnd(self, desktop, backend):
        backend._resolve_hwnd.return_value = 456
        backend.capture_window.return_value = self._result()
        desktop.capture("w.png", window="Notepad")
        backend.capture_window.assert_called_once_with(hwnd=456, output_path="w.png")


# ── lifecycle: launch / quit / wait ───────────────────────────────────
class TestLifecycle:
    def test_launch_returns_app(self, desktop):
        from naturo.process import ProcessInfo
        info = ProcessInfo(pid=1234, name="notepad")
        with patch("naturo.process.launch_app", return_value=info) as la:
            app = desktop.launch("notepad")
        assert isinstance(app, sdk.App)
        assert app.name == "notepad"
        assert app.pid == 1234
        la.assert_called_once_with(
            name="notepad", path=None, wait_until_ready=True, timeout=30.0,
            args=None, no_focus=False,
        )

    def test_quit_delegates(self, desktop):
        with patch("naturo.process.quit_app") as qa:
            desktop.quit("notepad", force=True)
        qa.assert_called_once_with("notepad", force=True)

    def test_wait_delegates(self, desktop, backend):
        sentinel = MagicMock(found=True)
        with patch("naturo.wait.wait_for_element", return_value=sentinel) as wfe:
            out = desktop.wait("Button:Save", timeout=5)
        assert out is sentinel
        wfe.assert_called_once_with(
            "Button:Save", timeout=5, poll_interval=0.1,
            window_title=None, hwnd=None, backend=backend,
        )


class TestApp:
    def _app(self, desktop):
        from naturo.process import ProcessInfo
        return sdk.App(desktop, ProcessInfo(pid=1, name="calc"))

    def test_app_type_targets_own_window(self, desktop, backend):
        app = self._app(desktop)
        with patch("naturo.sdk.smart_type_text", return_value="keystroke"):
            with patch.object(desktop, "type", wraps=desktop.type) as t:
                app.type("x")
        t.assert_called_once()
        assert t.call_args.kwargs["window"] == "calc"

    def test_app_context_manager_quits(self, desktop):
        app = self._app(desktop)
        with patch.object(desktop, "quit") as q:
            with app as entered:
                assert entered is app
        q.assert_called_once_with("calc", force=False)

    def test_app_capture_scopes_window(self, desktop, backend):
        app = self._app(desktop)
        backend._resolve_hwnd.return_value = 5
        backend.capture_window.return_value = CaptureResult(
            path="c.png", width=1, height=1, format="png",
        )
        app.capture("c.png")
        backend.capture_window.assert_called_once_with(hwnd=5, output_path="c.png")


# ── selector helpers ──────────────────────────────────────────────────
class TestSelectorHelpers:
    def test_parse_role_name(self):
        assert sdk._parse_selector("Button:Save") == ("Button", "Save")

    def test_parse_bare_name(self):
        assert sdk._parse_selector("Save") == (None, "Save")

    def test_match_role_and_name(self):
        assert sdk._element_matches("Button", "Save", "button", "save")
        assert not sdk._element_matches("Edit", "Save", "Button", "Save")

    def test_match_wildcard(self):
        assert sdk._element_matches("Edit", "filename box", None, "*file*")
        assert not sdk._element_matches("Edit", "other", None, "*file*")


# ── module-level convenience functions ────────────────────────────────
class TestModuleFunctions:
    def test_see_module_fn(self, backend):
        backend.get_element_tree.return_value = _elem(role="Window", name="N")
        with patch("naturo.sdk.get_backend", return_value=backend):
            el = naturo.see(window="N")
        assert isinstance(el, sdk.Element)

    def test_type_module_fn(self, backend):
        with patch("naturo.sdk.get_backend", return_value=backend):
            with patch("naturo.sdk.smart_type_text", return_value="value_pattern") as stt:
                method = naturo.type("hi")
        assert method == "value_pattern"
        stt.assert_called_once()

    def test_press_module_fn(self, backend):
        with patch("naturo.sdk.get_backend", return_value=backend):
            naturo.press("enter")
        backend.press_key.assert_called_once()

    def test_windows_module_fn(self, backend):
        backend.list_windows.return_value = []
        with patch("naturo.sdk.get_backend", return_value=backend):
            assert naturo.windows() == []

    def test_public_exports_present(self):
        for name in ("Desktop", "Session", "App", "Element", "see", "find",
                     "click", "type", "press", "get_value", "set_value",
                     "capture", "launch", "quit", "windows"):
            assert hasattr(naturo, name), name

    def test_wait_not_shadowing_submodule(self):
        # Top-level `naturo.wait` must stay the SUBMODULE, not the SDK verb,
        # so existing `naturo.wait.wait_for_element` (and its monkeypatching)
        # keep working. The verb lives on Desktop / naturo.sdk instead.
        import types
        assert isinstance(naturo.wait, types.ModuleType)
        assert callable(sdk.wait)

    def test_session_is_desktop(self):
        assert naturo.Session is naturo.Desktop


# ── examples import cleanly ───────────────────────────────────────────
class TestExamplesImport:
    @pytest.mark.parametrize("name", [
        "notepad_hello", "form_filler", "ui_inspector", "window_capture",
    ])
    def test_example_imports(self, name):
        examples_dir = Path(__file__).resolve().parents[1] / "examples"
        path = examples_dir / f"{name}.py"
        assert path.exists(), path
        spec = importlib.util.spec_from_file_location(f"_example_{name}", path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # executes top-level; must not raise
        assert hasattr(module, "main")
