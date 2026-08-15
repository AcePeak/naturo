"""Ergonomic in-process Python SDK — ``import naturo`` and automate, no subprocess.

naturo ships a CLI and an MCP server; this module adds the third first-class
surface Terminator's SDKs set the bar for: a clean importable API you drive from
Python without shelling out to ``naturo <cmd>``.

It is a *thin* wrapper. Every verb delegates to the exact code the CLI and MCP
surfaces already use, so the SDK cannot drift from them:

* windows/see/find/click/press/capture → the platform :class:`Backend`
  (``naturo.backends.base.get_backend``);
* ``type`` → :func:`naturo.actions.smart_type_text`, the shared IME-immune
  reliability ladder (ValuePattern → clipboard → keystroke) that keeps CJK/TSF
  input honest (#1219);
* ``see(cascade=True)`` → :func:`naturo.cascade.run_cascade`, the unified
  correctness-tagged tree (the moat);
* window-selector resolution → :func:`naturo.mcp._resolve.require_hwnd`, so a
  named-but-unresolvable window fails loudly instead of acting on the wrong one;
* launch/quit/wait → :mod:`naturo.process` and :func:`naturo.wait.wait_for_element`.

Two styles, same thin core:

    import naturo

    # module-level functions — quick, stateless
    tree = naturo.see(window="Notepad")
    naturo.type("hello", window="Notepad")
    el = naturo.find("Button:Save", window="Notepad")
    if el:
        el.click()
    naturo.capture("shot.png", window="Notepad")

    # or a reusable session / context-managed app
    with naturo.launch("notepad") as app:
        app.type("hello from naturo")
        app.capture("notepad.png")
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator, Optional, cast

from naturo.actions import smart_type_text
from naturo.backends.base import (
    Backend,
    CaptureResult,
    ElementInfo,
    MonitorInfo,
    WindowInfo,
    get_backend,
)
from naturo.mcp._resolve import require_hwnd

if TYPE_CHECKING:  # pragma: no cover — import only for type checkers
    from naturo.process import ProcessInfo
    from naturo.wait import WaitResult

__all__ = [
    "Desktop",
    "Session",
    "App",
    "Element",
    "see",
    "find",
    "click",
    "type",
    "press",
    "get_value",
    "set_value",
    "capture",
    "launch",
    "quit",
    "wait",
    "windows",
]


class Element:
    """A single UI element — a Pythonic wrapper over :class:`ElementInfo`.

    Carries the element's data (``role``, ``name``, ``value``, ``bounds``) plus
    the session it came from, so actions like :meth:`click` and :meth:`type`
    read naturally: ``sess.find("Button:Save").click()``.
    """

    def __init__(self, info: ElementInfo, desktop: "Desktop") -> None:
        self._info = info
        self._desktop = desktop

    # ── data accessors ───────────────────────────────────────────────
    @property
    def info(self) -> ElementInfo:
        """The underlying :class:`ElementInfo` dataclass."""
        return self._info

    @property
    def id(self) -> str:
        """Backend element identifier."""
        return self._info.id

    @property
    def role(self) -> str:
        """Control type / role (e.g. ``"Button"``, ``"Edit"``)."""
        return self._info.role

    @property
    def name(self) -> str:
        """Accessible name."""
        return self._info.name

    @property
    def value(self) -> Optional[str]:
        """Current value/text, if the element exposes one."""
        return self._info.value

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        """Screen bounds as ``(x, y, width, height)``."""
        i = self._info
        return (i.x, i.y, i.width, i.height)

    @property
    def center(self) -> tuple[int, int]:
        """Center point ``(x, y)`` of the element in screen coordinates."""
        i = self._info
        return (i.x + i.width // 2, i.y + i.height // 2)

    @property
    def children(self) -> list["Element"]:
        """Direct child elements, each wrapped as an :class:`Element`."""
        return [Element(c, self._desktop) for c in (self._info.children or [])]

    def descendants(self) -> Iterator["Element"]:
        """Yield every descendant element depth-first (self excluded)."""
        for child in self._info.children or []:
            wrapped = Element(child, self._desktop)
            yield wrapped
            yield from wrapped.descendants()

    def find(self, selector: str) -> Optional["Element"]:
        """Find a descendant by ``"Role:Name"`` or bare name (in-memory walk).

        This searches the already-fetched subtree — no new backend call. Use
        :meth:`Desktop.find` to query the live backend instead.
        """
        want_role, want_name = _parse_selector(selector)
        for el in self.descendants():
            if _element_matches(el.role, el.name, want_role, want_name):
                return el
        return None

    # ── actions ──────────────────────────────────────────────────────
    def click(self, button: str = "left", double: bool = False,
              input_mode: str = "normal") -> "Element":
        """Click the element's center. Returns ``self`` for chaining."""
        x, y = self.center
        self._desktop.backend.click(
            x=x, y=y, button=button, double=double, input_mode=input_mode,
        )
        return self

    def type(self, text: str, *, wpm: int = 120,
             input_mode: str = "normal") -> str:
        """Focus (via click) and type ``text`` through the IME-immune ladder.

        Returns the delivery method (``"value_pattern"`` | ``"clipboard_paste"``
        | ``"keystroke"``).
        """
        self.click()
        return smart_type_text(
            self._desktop.backend, text, input_mode=input_mode, wpm=wpm,
        )

    def get_value(self) -> Optional[dict]:
        """Read this element's current value via UIA patterns."""
        return self._desktop.backend.get_element_value(
            role=self._info.role, name=self._info.name,
        )

    def set_value(self, value: str) -> bool:
        """Set this element's value via UIA ValuePattern (no keystrokes)."""
        return bool(self._desktop._ext.set_element_value(
            text=value, role=self._info.role, name=self._info.name,
        ))

    def __repr__(self) -> str:
        return f"Element(role={self._info.role!r}, name={self._info.name!r})"


class Desktop:
    """A reusable automation session bound to one platform backend.

    All the core verbs live here as methods; the module-level functions
    (:func:`see`, :func:`type`, …) are thin shims that forward to a throwaway
    ``Desktop`` per call. Construct one explicitly to reuse a backend across
    many operations, or pass a fake backend for testing::

        d = naturo.Desktop()
        d.launch("notepad")
        d.type("hi", window="Notepad")
    """

    def __init__(self, backend: Optional[Backend] = None) -> None:
        self._backend = backend

    @property
    def backend(self) -> Backend:
        """The platform backend, auto-detected and cached on first use."""
        if self._backend is None:
            self._backend = get_backend()
        return self._backend

    @property
    def _ext(self) -> Any:
        """The backend viewed as ``Any`` for backend-specific surface.

        The abstract :class:`Backend` ABC deliberately under-specifies methods
        the concrete platform backends extend — ``get_element_tree(app=…, hwnd=…,
        pid=…)``, ``find_element(hwnd=…)``, ``hotkey(input_mode=…)`` and
        ``set_element_value(…)`` all live on the real backends (the MCP layer
        calls them the same way through an untyped handle). Routing those calls
        through this handle keeps the SDK honest about using that concrete
        surface without weakening typing on the ABC-defined verbs.
        """
        return cast(Any, self.backend)

    # ── observe ──────────────────────────────────────────────────────
    def windows(self) -> list[WindowInfo]:
        """List all visible top-level windows."""
        return self.backend.list_windows()

    def monitors(self) -> list[MonitorInfo]:
        """List all connected monitors/displays."""
        return self.backend.list_monitors()

    def see(
        self,
        *,
        window: Optional[str] = None,
        app: Optional[str] = None,
        hwnd: Optional[int] = None,
        pid: Optional[int] = None,
        depth: int = 0,
        accessibility_backend: str = "uia",
        cascade: bool = False,
    ) -> Optional[Element]:
        """Read a window's UI as a structured element tree.

        Returns the root :class:`Element` (walk ``.children`` / ``.descendants``
        / ``.find``), or ``None`` if no matching window. With ``cascade=True``
        runs the unified multi-framework recognition (UIA + CDP/JAB/COM), each
        node correctness-tagged — the fused tree that reaches web, Java and
        Excel-cell content plain accessibility misses.

        Args:
            window: Target window title (partial match). None = foreground.
            app: Target application name (partial match).
            hwnd: Window handle. Overrides app/window.
            pid: Process ID filter.
            depth: Tree depth; 0 = unlimited (default).
            accessibility_backend: "uia" (default), "msaa", "ia2", "jab", "auto".
            cascade: Run the unified correctness-tagged cascade.
        """
        if cascade:
            from naturo.cascade import run_cascade

            result = run_cascade(
                self.backend, app=app, window_title=window, hwnd=hwnd, pid=pid,
                depth=depth, backend_name="auto",
            )
            root = result.tree
        else:
            root = self._ext.get_element_tree(
                app=app, window_title=window, hwnd=hwnd, pid=pid,
                depth=depth, backend=accessibility_backend,
            )
        if root is None:
            return None
        return Element(root, self)

    def find(
        self,
        selector: str,
        *,
        window: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> Optional[Element]:
        """Find one element by ``"Role:Name"`` selector via the live backend.

        Returns an :class:`Element`, or ``None`` if nothing matches.
        """
        info = self._ext.find_element(
            selector=selector, window_title=window, hwnd=hwnd,
        )
        if info is None:
            return None
        return Element(info, self)

    # ── act ──────────────────────────────────────────────────────────
    def _focus(self, window: Optional[str], hwnd: Optional[int]) -> None:
        """Resolve a window selector loudly and focus it before acting.

        Mirrors the MCP surface (#957/#1291): a supplied-but-unresolvable
        selector raises ``WindowNotFoundError`` rather than silently acting on
        the foreground window.
        """
        if window is None and hwnd is None:
            return
        target = require_hwnd(self.backend, window_title=window, hwnd=hwnd)
        self.backend.focus_window(hwnd=target, title=window)

    def click(
        self,
        *,
        x: Optional[int] = None,
        y: Optional[int] = None,
        element_id: Optional[str] = None,
        button: str = "left",
        double: bool = False,
        input_mode: str = "normal",
        window: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> None:
        """Click at coordinates or on an element (by backend selector/ref).

        Pass ``window``/``hwnd`` to focus a specific window first.
        """
        self._focus(window, hwnd)
        self.backend.click(
            x=x, y=y, element_id=element_id, button=button, double=double,
            input_mode=input_mode,
        )

    def type(
        self,
        text: str,
        *,
        window: Optional[str] = None,
        hwnd: Optional[int] = None,
        wpm: int = 120,
        input_mode: str = "normal",
    ) -> str:
        """Type ``text`` through the shared IME-immune ladder.

        Optionally focus ``window``/``hwnd`` first (atomic focus+type, no
        cross-call foreground race). Returns the delivery method string.
        """
        self._focus(window, hwnd)
        return smart_type_text(self.backend, text, input_mode=input_mode, wpm=wpm)

    def press(
        self,
        key: str,
        *,
        count: int = 1,
        window: Optional[str] = None,
        hwnd: Optional[int] = None,
        input_mode: str = "normal",
    ) -> None:
        """Press a key or combo (``"enter"``, ``"ctrl+s"``) ``count`` times."""
        self._focus(window, hwnd)
        is_combo = "+" in key
        for _ in range(max(1, count)):
            if is_combo:
                keys = [k.strip() for k in key.replace("+", " ").split()]
                self._ext.hotkey(*keys, input_mode=input_mode)
            else:
                self.backend.press_key(key=key, input_mode=input_mode)

    def hotkey(self, *keys: str, input_mode: str = "normal") -> None:
        """Press a key combination given as separate keys (``"ctrl", "c"``)."""
        self._ext.hotkey(*keys, input_mode=input_mode)

    def scroll(self, direction: str = "down", amount: int = 3,
               x: Optional[int] = None, y: Optional[int] = None) -> None:
        """Scroll the mouse wheel ``amount`` units up/down."""
        self.backend.scroll(direction=direction, amount=amount, x=x, y=y)

    def get_value(
        self,
        *,
        ref: Optional[str] = None,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        window: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> Optional[dict]:
        """Read a UI element's current value via UIA patterns."""
        return self.backend.get_element_value(
            ref=ref, automation_id=automation_id, role=role, name=name,
            window_title=window, hwnd=hwnd,
        )

    def set_value(
        self,
        value: str,
        *,
        automation_id: Optional[str] = None,
        role: Optional[str] = None,
        name: Optional[str] = None,
        window: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> bool:
        """Set a UI element's value via UIA ValuePattern (bypasses SendInput)."""
        target = require_hwnd(self.backend, window_title=window, hwnd=hwnd)
        return bool(self._ext.set_element_value(
            text=value, hwnd=target, automation_id=automation_id,
            role=role, name=name,
        ))

    def capture(
        self,
        path: str = "capture.png",
        *,
        window: Optional[str] = None,
        hwnd: Optional[int] = None,
        screen: Optional[int] = None,
    ) -> CaptureResult:
        """Capture a screenshot to ``path``.

        Pass ``window``/``hwnd`` to capture one window, or ``screen`` (monitor
        index) for a specific display; with none of them, captures the primary
        screen. Returns a :class:`CaptureResult`.
        """
        if hwnd is not None:
            return self.backend.capture_window(hwnd=hwnd, output_path=path)
        if window is not None:
            if hasattr(self.backend, "_resolve_hwnd"):
                resolved = require_hwnd(self.backend, window_title=window)
                return self.backend.capture_window(hwnd=resolved, output_path=path)
            return self.backend.capture_window(window_title=window, output_path=path)
        return self.backend.capture_screen(
            screen_index=screen or 0, output_path=path,
        )

    # ── lifecycle ────────────────────────────────────────────────────
    def launch(
        self,
        name: Optional[str] = None,
        *,
        path: Optional[str] = None,
        wait: bool = True,
        timeout: float = 30.0,
        args: Optional[list[str]] = None,
        no_focus: bool = False,
    ) -> "App":
        """Launch an application and return an :class:`App` handle.

        By default waits until the app has created a window (``wait=True``).
        """
        from naturo.process import launch_app

        info = launch_app(
            name=name, path=path, wait_until_ready=wait, timeout=timeout,
            args=args, no_focus=no_focus,
        )
        return App(self, info)

    def quit(self, name: str, *, force: bool = False) -> None:
        """Quit an application by name (verified gone before returning)."""
        from naturo.process import quit_app

        quit_app(name, force=force)

    def wait(
        self,
        selector: str,
        *,
        timeout: float = 10.0,
        poll_interval: float = 0.1,
        window: Optional[str] = None,
        hwnd: Optional[int] = None,
    ) -> "WaitResult":
        """Poll until an element matching ``selector`` appears (or timeout).

        Returns a :class:`~naturo.wait.WaitResult` (``.found`` / ``.element``).
        """
        from naturo.wait import wait_for_element

        return wait_for_element(
            selector, timeout=timeout, poll_interval=poll_interval,
            window_title=window, hwnd=hwnd, backend=self.backend,
        )


# ``Session`` reads well for a long-lived automation script; same class.
Session = Desktop


class App:
    """A handle to a launched application, scoping verbs to that app.

    Returned by :meth:`Desktop.launch` / :func:`launch`. Doubles as a context
    manager that quits the app on exit::

        with naturo.launch("notepad") as app:
            app.type("hello")
    """

    def __init__(self, desktop: Desktop, info: "ProcessInfo") -> None:
        self._desktop = desktop
        self._info = info

    @property
    def info(self) -> "ProcessInfo":
        """The :class:`~naturo.process.ProcessInfo` for the launched app."""
        return self._info

    @property
    def name(self) -> str:
        """Resolved application/process name."""
        return self._info.name

    @property
    def pid(self) -> int:
        """Process ID."""
        return self._info.pid

    @property
    def desktop(self) -> Desktop:
        """The owning :class:`Desktop` session."""
        return self._desktop

    def see(self, **kwargs) -> Optional[Element]:
        """:meth:`Desktop.see` scoped to this app."""
        kwargs.setdefault("app", self.name)
        return self._desktop.see(**kwargs)

    def find(self, selector: str, **kwargs) -> Optional[Element]:
        """:meth:`Desktop.find` scoped to this app's window title."""
        kwargs.setdefault("window", self.name)
        return self._desktop.find(selector, **kwargs)

    def type(self, text: str, **kwargs) -> str:
        """:meth:`Desktop.type` targeting this app's window."""
        kwargs.setdefault("window", self.name)
        return self._desktop.type(text, **kwargs)

    def press(self, key: str, **kwargs) -> None:
        """:meth:`Desktop.press` targeting this app's window."""
        kwargs.setdefault("window", self.name)
        self._desktop.press(key, **kwargs)

    def click(self, **kwargs) -> None:
        """:meth:`Desktop.click` targeting this app's window."""
        kwargs.setdefault("window", self.name)
        self._desktop.click(**kwargs)

    def capture(self, path: str = "capture.png", **kwargs) -> CaptureResult:
        """:meth:`Desktop.capture` of this app's window."""
        kwargs.setdefault("window", self.name)
        return self._desktop.capture(path, **kwargs)

    def quit(self, *, force: bool = False) -> None:
        """Quit this application."""
        self._desktop.quit(self.name, force=force)

    def __enter__(self) -> "App":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.quit()

    def __repr__(self) -> str:
        return f"App(name={self.name!r}, pid={self.pid})"


# ── selector helpers (in-memory Element.find) ────────────────────────
def _parse_selector(selector: str) -> tuple[Optional[str], Optional[str]]:
    """Split a ``"Role:Name"`` selector into ``(role, name)``.

    A bare string with no ``:`` is treated as a name filter.
    """
    if ":" in selector:
        role, name = selector.split(":", 1)
        return (role.strip() or None, name.strip() or None)
    return (None, selector.strip() or None)


def _element_matches(role: str, name: str, want_role: Optional[str],
                     want_name: Optional[str]) -> bool:
    """Case-insensitive role/name match, ``*`` wildcards allowed in the name."""
    if want_role is not None and want_role.lower() != (role or "").lower():
        return False
    if want_name is not None:
        want = want_name.lower()
        got = (name or "").lower()
        if "*" in want:
            core = want.strip("*")
            if core and core not in got:
                return False
        elif want != got:
            return False
    return True


# ── module-level convenience functions ───────────────────────────────
# Each forwards to a fresh Desktop (which lazily resolves the backend), so the
# functions stay stateless and always honour a patched get_backend.
def see(**kwargs) -> Optional[Element]:
    """Module-level :meth:`Desktop.see`."""
    return Desktop().see(**kwargs)


def find(selector: str, **kwargs) -> Optional[Element]:
    """Module-level :meth:`Desktop.find`."""
    return Desktop().find(selector, **kwargs)


def click(**kwargs) -> None:
    """Module-level :meth:`Desktop.click`."""
    Desktop().click(**kwargs)


def type(text: str, **kwargs) -> str:  # noqa: A001 — deliberate ergonomic verb
    """Module-level :meth:`Desktop.type` (IME-immune)."""
    return Desktop().type(text, **kwargs)


def press(key: str, **kwargs) -> None:
    """Module-level :meth:`Desktop.press`."""
    Desktop().press(key, **kwargs)


def get_value(**kwargs) -> Optional[dict]:
    """Module-level :meth:`Desktop.get_value`."""
    return Desktop().get_value(**kwargs)


def set_value(value: str, **kwargs) -> bool:
    """Module-level :meth:`Desktop.set_value`."""
    return Desktop().set_value(value, **kwargs)


def capture(path: str = "capture.png", **kwargs) -> CaptureResult:
    """Module-level :meth:`Desktop.capture`."""
    return Desktop().capture(path, **kwargs)


def launch(name: Optional[str] = None, **kwargs) -> App:
    """Module-level :meth:`Desktop.launch`."""
    return Desktop().launch(name, **kwargs)


def quit(name: str, **kwargs) -> None:  # noqa: A001 — deliberate ergonomic verb
    """Module-level :meth:`Desktop.quit`."""
    Desktop().quit(name, **kwargs)


def wait(selector: str, **kwargs) -> "WaitResult":
    """Module-level :meth:`Desktop.wait`."""
    return Desktop().wait(selector, **kwargs)


def windows() -> list[WindowInfo]:
    """Module-level :meth:`Desktop.windows`."""
    return Desktop().windows()
