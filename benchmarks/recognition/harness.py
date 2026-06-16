"""Recognition-coverage benchmark harness (issue #931).

This harness measures, on the *same* live application, how many UI elements
naturo recognizes two ways:

1. **Full cascade** — naturo's multi-framework engine
   (UIA + MSAA/IA2 + Java Access Bridge + Electron/CDP + vision fusion).
   This is what naturo actually sees.
2. **UIA-only baseline** — naturo restricted to the UIA accessibility tree.
   This is what a UIA-only competitor (Windows-MCP, Terminator, UFO²) would
   see, measured honestly with naturo's *own* engine so the comparison is
   apples-to-apples on identical app state.

The difference (``delta``) is naturo's multi-framework advantage, and the
``extra_sources`` breakdown shows *which* provider (CDP, JAB, vision) found
the elements that UIA alone could not.

Why this is fair
----------------
* Both measurements run against the same window in the same state, back to
  back, so the only variable is which providers are enabled.
* The UIA-only number is produced by naturo itself (``backend_name="uia"``),
  not by a hobbled re-implementation — it is exactly the tree a UIA-only tool
  would walk.
* No competitor needs to be installed: we simulate the UIA-only ceiling by
  disabling naturo's extra providers.

Reproducibility
---------------
For Chromium/Electron apps we ship a local HTML fixture
(``fixtures/webapp.html``) and drive Chrome with a dedicated, throwaway user
profile and ``--remote-debugging-port``.  This makes the web-content delta
deterministic and offline — no network, no live website drift.

Public entry points
--------------------
* :func:`measure_window` — measure an *already-open* window by HWND/PID.
* :func:`ChromiumFixtureApp` — launch/stop a controlled Chromium app on the
  bundled fixture (the reproducible Electron-class case).
* :func:`measure_running_app` — find a running app by window-title substring
  and measure it (for ad-hoc Electron/Java apps available on the desktop).
"""
from __future__ import annotations

import logging
import socket
import subprocess
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from naturo.backends.base import get_backend
from naturo.cascade import _flatten, run_cascade

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
DEFAULT_CDP_PORT = 9222


@dataclass
class CoverageResult:
    """Recognition-coverage measurement for a single application.

    Attributes:
        app: Human-readable application label (e.g. ``"Chrome (web app)"``).
        framework: The non-UIA framework that the cascade exercises
            (``"Electron/CDP"``, ``"Java Access Bridge"``, ...).
        uia_only_count: Element count from the UIA-only baseline (what a
            UIA-only rival would see).
        cascade_count: Element count from the full multi-framework cascade.
        extra_sources: Per-provider count of elements the cascade added on top
            of UIA (e.g. ``{"cdp": 34}``).
        sample_extra_names: A few example labels of elements only the cascade
            recognized — concrete evidence of the advantage.
        notes: Free-form notes (e.g. gaps, caveats).
    """

    app: str
    framework: str
    uia_only_count: int
    cascade_count: int
    extra_sources: dict = field(default_factory=dict)
    sample_extra_names: List[str] = field(default_factory=list)
    notes: str = ""

    @property
    def delta(self) -> int:
        """Number of extra elements the full cascade recognizes over UIA-only."""
        return self.cascade_count - self.uia_only_count

    def to_dict(self) -> dict:
        """Return a JSON-serialisable representation of the result."""
        return {
            "app": self.app,
            "framework": self.framework,
            "uia_only_count": self.uia_only_count,
            "cascade_count": self.cascade_count,
            "delta": self.delta,
            "extra_sources": dict(self.extra_sources),
            "sample_extra_names": list(self.sample_extra_names),
            "notes": self.notes,
        }


def _provider_counts(stats) -> dict:
    """Map provider name -> recognized element count for ``status == "ok"``.

    Args:
        stats: A :class:`naturo.cascade.CascadeStats` instance.

    Returns:
        Dict of provider name to element count, only for providers that
        successfully contributed elements.
    """
    counts: dict = {}
    for provider in stats.providers:
        if provider.status == "ok" and provider.elements > 0:
            counts[provider.name] = counts.get(provider.name, 0) + provider.elements
    return counts


def measure_window(
    *,
    app: str,
    framework: str,
    hwnd: Optional[int] = None,
    pid: Optional[int] = None,
    window_title: Optional[str] = None,
    depth: int = 15,
    notes: str = "",
) -> CoverageResult:
    """Measure UIA-only vs full-cascade recognition on one open window.

    Runs the cascade twice against the same window, back to back:
    ``backend_name="uia"`` for the baseline and ``backend_name="auto"`` for the
    full multi-framework cascade.

    Args:
        app: Human-readable application label for the report.
        framework: The non-UIA framework exercised (for the report).
        hwnd: Target window handle.  At least one of ``hwnd``, ``pid`` or
            ``window_title`` must be given.
        pid: Target process id (helps CDP/JAB provider discovery).
        window_title: Window-title filter (substring match by the backend).
        depth: Maximum accessibility-tree depth to walk.
        notes: Free-form notes to attach to the result.

    Returns:
        A :class:`CoverageResult` capturing both counts, the delta and the
        provider breakdown.

    Raises:
        ValueError: If none of ``hwnd``/``pid``/``window_title`` is provided.
    """
    if hwnd is None and pid is None and window_title is None:
        raise ValueError("Provide at least one of hwnd, pid or window_title.")

    backend = get_backend()

    uia = run_cascade(
        backend, hwnd=hwnd, pid=pid, window_title=window_title,
        depth=depth, backend_name="uia",
    )
    full = run_cascade(
        backend, hwnd=hwnd, pid=pid, window_title=window_title,
        depth=depth, backend_name="auto",
    )

    full_counts = _provider_counts(full.stats)
    extra_sources = {
        name: count for name, count in full_counts.items() if name != "uia"
    }

    sample_extra_names: List[str] = []
    if full.tree is not None:
        for element in _flatten(full.tree):
            source = (element.properties or {}).get("source")
            if source and source != "uia":
                label = (element.name or element.role or "").strip()
                if label and label not in sample_extra_names:
                    sample_extra_names.append(label)
            if len(sample_extra_names) >= 8:
                break

    return CoverageResult(
        app=app,
        framework=framework,
        uia_only_count=uia.stats.total_elements,
        cascade_count=full.stats.total_elements,
        extra_sources=extra_sources,
        sample_extra_names=sample_extra_names,
        notes=notes,
    )


def _find_chrome_executable() -> Optional[str]:
    """Locate a Chrome/Edge executable for the Chromium fixture.

    Returns:
        Absolute path to a Chromium-family browser, or ``None`` if none found.
    """
    import os

    candidates = [
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                     "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                     "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                     "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                     "Microsoft", "Edge", "Application", "msedge.exe"),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _port_is_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Return ``True`` if a TCP connection to ``host:port`` succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


class ChromiumFixtureApp:
    """Launch and control a Chromium browser on the bundled HTML fixture.

    This provides the reproducible Electron-class case: a Chromium renderer
    whose web content is invisible to UIA but fully recognized by naturo's CDP
    provider.  Electron apps embed the exact same Chromium content layer, so a
    delta here is representative of the Electron delta.

    Use as a context manager::

        with ChromiumFixtureApp() as app:
            result = app.measure()

    Modern Chromium rejects CDP WebSocket connections unless launched with
    ``--remote-allow-origins`` — the launch arguments below include it.
    """

    #: Window title rendered by ``fixtures/webapp.html`` (used to find the HWND).
    WINDOW_TITLE_SUBSTRING = "Naturo Recognition Benchmark"

    def __init__(
        self,
        *,
        fixture: str = "webapp.html",
        port: int = DEFAULT_CDP_PORT,
        chrome_path: Optional[str] = None,
    ) -> None:
        """Initialise the controller.

        Args:
            fixture: HTML fixture filename inside ``fixtures/``.
            port: CDP remote-debugging port to use.
            chrome_path: Override the auto-detected browser executable.
        """
        self.fixture_path = FIXTURES_DIR / fixture
        self.port = port
        self.chrome_path = chrome_path or _find_chrome_executable()
        self._process: Optional[subprocess.Popen] = None
        self._user_data_dir: Optional[str] = None

    @property
    def available(self) -> bool:
        """Whether a Chromium browser and the fixture file are both present."""
        return self.chrome_path is not None and self.fixture_path.is_file()

    def start(self, ready_timeout: float = 30.0) -> None:
        """Launch the browser and wait for both CDP and page load.

        Args:
            ready_timeout: Maximum seconds to wait for the CDP endpoint and a
                rendered page.

        Raises:
            RuntimeError: If no browser is available, or the CDP endpoint /
                page does not become ready within ``ready_timeout``.
        """
        import tempfile

        if not self.available or self.chrome_path is None:
            raise RuntimeError(
                "Chromium fixture unavailable: "
                f"chrome={self.chrome_path!r}, fixture={self.fixture_path!r}"
            )

        self._user_data_dir = tempfile.mkdtemp(prefix="naturo_bench_chrome_")
        args: List[str] = [
            self.chrome_path,
            f"--remote-debugging-port={self.port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={self._user_data_dir}",
            "--new-window",
            "--no-first-run",
            "--no-default-browser-check",
            "--allow-file-access-from-files",
            self.fixture_path.as_uri(),
        ]
        logger.info("Launching Chromium fixture: %s", self.fixture_path)
        self._process = subprocess.Popen(args)

        deadline = time.monotonic() + ready_timeout
        while time.monotonic() < deadline:
            if _port_is_open("127.0.0.1", self.port):
                break
            time.sleep(0.5)
        else:
            self.stop()
            raise RuntimeError(
                f"CDP endpoint did not open on port {self.port} within "
                f"{ready_timeout:.0f}s."
            )

        # Wait for the page to actually finish loading so the DOM is populated.
        if not self._wait_page_loaded(deadline):
            self.stop()
            raise RuntimeError("Fixture page did not finish loading in time.")

    def _wait_page_loaded(self, deadline: float) -> bool:
        """Poll the CDP ``/json`` list until the fixture page reports complete.

        Args:
            deadline: ``time.monotonic()`` value after which to give up.

        Returns:
            ``True`` once the fixture page is the active target, else ``False``
            on timeout.
        """
        url = f"http://127.0.0.1:{self.port}/json"
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    import json

                    targets = json.loads(response.read().decode("utf-8"))
                for target in targets:
                    if (
                        target.get("type") == "page"
                        and "webapp.html" in target.get("url", "")
                    ):
                        time.sleep(1.0)  # settle the render
                        return True
            except (OSError, ValueError):
                pass
            time.sleep(0.5)
        return False

    def find_window(self):
        """Find the fixture browser window via the backend.

        Returns:
            A window-info object (with ``hwnd``/``pid``) for the fixture
            window, or ``None`` if it cannot be located.
        """
        backend = get_backend()
        for window in backend.list_windows():
            if self.WINDOW_TITLE_SUBSTRING in (window.title or ""):
                return window
        return None

    def measure(self, depth: int = 15) -> CoverageResult:
        """Measure recognition coverage on the fixture window.

        Args:
            depth: Maximum accessibility-tree depth to walk.

        Returns:
            A :class:`CoverageResult` for the Chromium fixture app.

        Raises:
            RuntimeError: If the fixture window cannot be found.
        """
        window = self.find_window()
        if window is None:
            raise RuntimeError(
                "Could not locate the Chromium fixture window. "
                "Did the browser launch and render the fixture?"
            )
        return measure_window(
            app="Chrome (local web/Electron-class app)",
            framework="Electron/CDP",
            hwnd=window.hwnd,
            pid=window.pid,
            depth=depth,
            notes=(
                "Web content is rendered by Chromium and is invisible to the "
                "UIA tree; only the CDP provider recognizes the page's "
                "interactive elements. Electron apps embed the identical "
                "Chromium content layer, so this delta is representative."
            ),
        )

    def stop(self) -> None:
        """Terminate the browser and remove its throwaway profile."""
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=10)
            except (OSError, subprocess.TimeoutExpired):
                try:
                    self._process.kill()
                except OSError:
                    pass
            self._process = None
        if self._user_data_dir is not None:
            import shutil

            shutil.rmtree(self._user_data_dir, ignore_errors=True)
            self._user_data_dir = None

    def __enter__(self) -> "ChromiumFixtureApp":
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.stop()


def measure_running_app(
    *,
    app: str,
    framework: str,
    title_substring: str,
    depth: int = 15,
    notes: str = "",
) -> Optional[CoverageResult]:
    """Measure an already-running app located by window-title substring.

    Useful for ad-hoc apps available on the current desktop (a JetBrains IDE,
    DBeaver, Feishu, ...) that are not part of the reproducible fixture set.

    Args:
        app: Human-readable application label for the report.
        framework: The non-UIA framework exercised (for the report).
        title_substring: Case-sensitive substring to match against window
            titles.
        depth: Maximum accessibility-tree depth to walk.
        notes: Free-form notes to attach to the result.

    Returns:
        A :class:`CoverageResult`, or ``None`` if no matching window is open.
    """
    backend = get_backend()
    for window in backend.list_windows():
        if title_substring in (window.title or ""):
            return measure_window(
                app=app,
                framework=framework,
                hwnd=window.hwnd,
                pid=window.pid,
                depth=depth,
                notes=notes,
            )
    return None
