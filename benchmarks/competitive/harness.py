"""Competitive benchmark harness — naturo vs real, installed OSS rivals (D1).

Where ``benchmarks/recognition/`` compares naturo's full cascade against
naturo's *own* UIA-only baseline (a fair proxy for a UIA-only rival), this
harness runs the **actual rival libraries** — installed from PyPI — against the
**same** live window, so the published coverage matrix is reproducible from real
runs, not authored from source declarations.

Each rival is an :class:`Adapter` that reports how many interactive UI elements
*it* recognizes on a given window:

* :class:`NaturoAdapter`   -- naturo's fused multi-framework cascade
  (``run_cascade(..., backend_name="auto")``): UIA + MSAA/IA2 + JAB + CDP + …
* :class:`PywinautoAdapter` -- ``pywinauto`` walking its UIA control tree. This
  is the strongest UIA-only OSS baseline; it sees UIA-native apps but returns
  ~nothing on the Chromium/Electron content layer, Java/Swing (JAB) and the
  Excel cell grid, which collapse to one opaque node in UIA.
* :class:`PyAutoGUIAdapter` -- ``pyautogui`` has **no element model at all**
  (pixels/coordinates only), so it recognizes **zero** UI elements on every
  app. Represented honestly as a constant 0, not omitted.

An adapter returns ``None`` (not 0) when it cannot run on the host at all
(library not installed, non-Windows) — the matrix renders that ``blocked: needs
env``, never a guessed number. A ``0`` means the tool *ran* and recognized
nothing: that is the moat cell.

The pure matrix aggregation + Markdown rendering lives in ``matrix.py`` (no
naturo/rival imports → Linux-collectable, test-pinned). This module holds the
Windows-only runtime that produces the :class:`CompetitiveResult` rows.
"""
from __future__ import annotations

import importlib.util
import logging
from typing import Dict, List, Optional

from benchmarks.competitive.matrix import NATURO, CompetitiveResult

logger = logging.getLogger(__name__)


def _installed(module: str) -> bool:
    """Return ``True`` if ``module`` is importable on this host."""
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


_comtypes_prepared = False


def _prepare_comtypes_gen() -> None:
    """Point comtypes' generated type-library cache at a fresh writable dir so
    pywinauto can import here.

    Under a system Python the default ``comtypes/gen`` cache is read-only
    (PermissionError) and can go stale ("Typelib different than module"); the
    ``from pywinauto import Desktop`` below then fails and the rival is silently
    scored as unavailable — understating pywinauto, not naturo. naturo self-heals
    this (#1219/#1220); the rival does not, so we provision a writable gen dir
    once before importing it. Idempotent; best-effort.
    """
    global _comtypes_prepared
    if _comtypes_prepared:
        return
    _comtypes_prepared = True
    import os
    import sys
    import tempfile

    gen_dir = tempfile.mkdtemp(prefix="naturo_bench_ctgen_")
    os.environ.setdefault("COMTYPES_GEN_DIR", gen_dir)
    try:
        import comtypes
        import comtypes.client
        comtypes.client.gen_dir = gen_dir
        import comtypes.gen
        comtypes.gen.__path__ = [gen_dir]  # force lookups into the empty dir
        for mod in [m for m in sys.modules if m.startswith("comtypes.gen.")]:
            del sys.modules[mod]
    except Exception:
        pass  # no comtypes (non-Windows / not installed) — nothing to prepare


# Run at import: this module is imported before naturo (lazily loaded inside the
# adapters below) touches comtypes, so the gen dir is redirected to a writable
# location first. Calling it only inside count_elements was too late — naturo
# imports comtypes first and locks the gen dir to the read-only default, leaving
# pywinauto falsely scored `blocked: needs env` in a real run (verified on host).
_prepare_comtypes_gen()


class Adapter:
    """Base class: how many interactive elements does one tool recognize?"""

    #: Tool key used in the matrix (must match ``matrix`` DISPLAY_NAMES keys).
    name: str = ""

    @property
    def available(self) -> bool:
        """Whether this tool can run on the current host."""
        raise NotImplementedError

    def count_elements(
        self,
        *,
        hwnd: Optional[int] = None,
        pid: Optional[int] = None,
        window_title: Optional[str] = None,
        depth: int = 15,
    ) -> Optional[int]:
        """Count interactive elements this tool recognizes on one window.

        Returns an ``int`` (possibly 0 — ran but saw nothing), or ``None`` when
        the tool could not run at all (→ ``blocked: needs env`` in the matrix).
        """
        raise NotImplementedError


class NaturoAdapter(Adapter):
    """naturo's fused multi-framework cascade (the engine under test)."""

    name = NATURO

    @property
    def available(self) -> bool:
        return _installed("naturo")

    def count_elements(
        self,
        *,
        hwnd: Optional[int] = None,
        pid: Optional[int] = None,
        window_title: Optional[str] = None,
        depth: int = 15,
    ) -> Optional[int]:
        try:
            from naturo.backends.base import get_backend
            from naturo.cascade import run_cascade
        except Exception as exc:  # pragma: no cover - import guard
            logger.warning("naturo unavailable: %s", exc)
            return None
        try:
            result = run_cascade(
                get_backend(),
                hwnd=hwnd,
                pid=pid,
                window_title=window_title,
                depth=depth,
                backend_name="auto",
            )
        except Exception as exc:
            logger.warning("naturo cascade failed: %s", exc)
            return None
        return result.stats.total_elements


class PywinautoAdapter(Adapter):
    """``pywinauto`` walking its own UIA control tree (strongest UIA-only rival).

    Fair/best config: the UIA backend (``pywinauto`` also has a legacy win32
    backend, but UIA is its most capable tree and the honest ceiling for a
    UIA-only tool). Counts every descendant control of the target window.
    """

    name = "pywinauto"

    @property
    def available(self) -> bool:
        # pywinauto is Windows-only (imports win32 at module load).
        return _installed("pywinauto")

    def count_elements(
        self,
        *,
        hwnd: Optional[int] = None,
        pid: Optional[int] = None,
        window_title: Optional[str] = None,
        depth: int = 15,
    ) -> Optional[int]:
        _prepare_comtypes_gen()  # unblock pywinauto's comtypes gen-cache
        try:
            from pywinauto import Desktop
        except Exception as exc:  # pragma: no cover - Windows-only import
            logger.warning("pywinauto unavailable: %s", exc)
            return None
        try:
            desktop = Desktop(backend="uia")
            if hwnd is not None:
                window = desktop.window(handle=hwnd)
            elif window_title is not None:
                window = desktop.window(title_re=f".*{window_title}.*")
            elif pid is not None:
                window = desktop.window(process=pid)
            else:
                raise ValueError("Provide hwnd, pid or window_title.")
            # descendants() enumerates the full UIA control subtree — exactly the
            # tree a UIA-only tool (Windows-MCP/Terminator/UFO²) would walk.
            return len(window.descendants())
        except Exception as exc:
            logger.warning("pywinauto walk failed: %s", exc)
            return None


class PyAutoGUIAdapter(Adapter):
    """``pyautogui`` — pixel/coordinate automation with **no element model**.

    PyAutoGUI cannot enumerate UI elements at all (it offers keyboard/mouse
    control and screenshot pixel/image matching). Its honest recognized-element
    count is therefore **0** on every application — reported, not hidden, so the
    matrix shows why an agent builder cannot ask it "what's on screen?".
    """

    name = "pyautogui"

    @property
    def available(self) -> bool:
        return _installed("pyautogui")

    def count_elements(
        self,
        *,
        hwnd: Optional[int] = None,
        pid: Optional[int] = None,
        window_title: Optional[str] = None,
        depth: int = 15,
    ) -> Optional[int]:
        # No accessibility/element tree exists in PyAutoGUI's model.
        return 0


#: Default adapter set for the competitive matrix, naturo first.
def default_adapters() -> List[Adapter]:
    """Return the default adapter set (naturo + reproducible OSS rivals)."""
    return [NaturoAdapter(), PywinautoAdapter(), PyAutoGUIAdapter()]


def measure_competitive(
    *,
    app: str,
    framework: str,
    hwnd: Optional[int] = None,
    pid: Optional[int] = None,
    window_title: Optional[str] = None,
    depth: int = 15,
    notes: str = "",
    adapters: Optional[List[Adapter]] = None,
) -> CompetitiveResult:
    """Run every adapter against the same window and collect a matrix row.

    Args:
        app: Human-readable application label.
        framework: UI framework exercised (``"Electron/CDP"``, ``"UIA"`` ...).
        hwnd/pid/window_title: How to target the window (at least one).
        depth: Max accessibility-tree depth for tools that honour it.
        notes: Provenance/caveat note carried into the report.
        adapters: Override the adapter set (defaults to :func:`default_adapters`).

    Returns:
        A :class:`CompetitiveResult` with one ``counts`` entry per tool
        (``None`` for tools that could not run here).
    """
    adapters = adapters if adapters is not None else default_adapters()
    counts: Dict[str, Optional[int]] = {}
    for adapter in adapters:
        if not adapter.available:
            counts[adapter.name] = None
            continue
        counts[adapter.name] = adapter.count_elements(
            hwnd=hwnd, pid=pid, window_title=window_title, depth=depth
        )
    return CompetitiveResult(app=app, framework=framework, counts=counts, notes=notes)
