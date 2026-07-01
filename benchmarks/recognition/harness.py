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
* :func:`ElectronFixtureApp` — launch/stop an *owned, real* Electron process
  (``fixtures/electron/``) and measure it. This is a genuine Electron app, not
  a browser standing in for one, so the CDP delta it shows is the literal
  Electron case rather than a representative proxy.
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
from naturo.cascade import _flatten, recognition_summary, run_cascade
from naturo.cascade._correctness import DETERMINISTIC, technique_class

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
DEFAULT_CDP_PORT = 9222
#: CDP port for the owned Electron fixture — deliberately distinct from the
#: Chromium fixture's 9222 so both can run back-to-back without colliding.
DEFAULT_ELECTRON_CDP_PORT = 9333


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
    # M2: fusion tags from the M1 recognition_summary (deterministic-first
    # techniques + a deterministic/uncertain node breakdown).
    techniques: List[str] = field(default_factory=list)
    correctness_counts: dict = field(default_factory=dict)

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
            "techniques": list(self.techniques),
            "correctness_counts": dict(self.correctness_counts),
            "degree": adaptation_degree(self),
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


def _degree_fields_from_summary(summary: dict) -> tuple[List[str], dict]:
    """Derive (techniques, correctness_counts) from an M1 recognition_summary.

    ``techniques`` is deterministic-first (the contract in
    docs/RECOGNITION_TREE.md); ``correctness_counts`` splits the recognized
    nodes into ``deterministic`` vs ``uncertain``.
    """
    by_technique = summary.get("by_technique", {}) or {}
    total = summary.get("total_nodes", 0) or 0
    uncertain = summary.get("uncertain_nodes", 0) or 0
    techniques = sorted(
        by_technique.keys(),
        key=lambda t: (technique_class(t) != DETERMINISTIC, t),
    )
    counts = {"deterministic": total - uncertain, "uncertain": uncertain}
    return techniques, counts


def adaptation_degree(result: "CoverageResult") -> str:
    """Classify a measured result into an honest adaptation-degree class.

    See docs/design/software-adaptation-degree.md §2. This is a coarse class,
    never a false-precision score:

    * ``full``           -- a deterministic non-UIA framework (cdp/jab/com/ia2/
      msaa) adds net elements (``delta > 0``). The moat case.
    * ``uncertain-only`` -- the only non-UIA contribution is image/OCR/AI.
    * ``uia-only``       -- only UIA adds value (a UIA-only rival would tie).

    ``blocked: needs env`` is decided at collection time (a framework that
    cannot be exercised on the host), not here.
    """
    techniques = result.techniques or []
    deterministic_non_uia = [
        t for t in techniques
        if technique_class(t) == DETERMINISTIC and t != "uia"
    ]
    uncertain = [t for t in techniques if technique_class(t) != DETERMINISTIC]
    if deterministic_non_uia and result.delta > 0:
        return "full"
    if uncertain and not deterministic_non_uia and result.delta > 0:
        return "uncertain-only"
    return "uia-only"


def measure_window(
    *,
    app: str,
    framework: str,
    hwnd: Optional[int] = None,
    pid: Optional[int] = None,
    window_title: Optional[str] = None,
    depth: int = 15,
    notes: str = "",
    run_ocr: bool = False,
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
        depth=depth, backend_name="auto", run_ocr=run_ocr,
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

    # M2: fusion tags (techniques + deterministic/uncertain split) from the
    # same fused tree, via the M1 recognition_summary.
    techniques: List[str] = []
    correctness_counts: dict = {}
    if full.tree is not None:
        techniques, correctness_counts = _degree_fields_from_summary(
            recognition_summary(full.tree)
        )

    return CoverageResult(
        app=app,
        framework=framework,
        uia_only_count=uia.stats.total_elements,
        cascade_count=full.stats.total_elements,
        extra_sources=extra_sources,
        sample_extra_names=sample_extra_names,
        notes=notes,
        techniques=techniques,
        correctness_counts=correctness_counts,
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


def _resolve_electron_binary(fixture_dir: Path) -> Optional[str]:
    """Locate the installed Electron executable for the fixture.

    Electron's npm package records the path to its bundled binary (relative to
    the package root) in ``node_modules/electron/path.txt``.  We honour that
    first and fall back to the conventional ``dist/electron.exe`` location.

    Args:
        fixture_dir: The ``fixtures/electron`` directory containing
            ``node_modules`` after ``npm install``.

    Returns:
        Absolute path to ``electron.exe``, or ``None`` if Electron is not
        installed (``npm install`` has not been run).
    """
    electron_pkg = fixture_dir / "node_modules" / "electron"
    path_txt = electron_pkg / "path.txt"
    if path_txt.is_file():
        try:
            relative = path_txt.read_text(encoding="utf-8").strip()
        except OSError:
            relative = ""
        if relative:
            candidate = electron_pkg / "dist" / relative
            if candidate.is_file():
                return str(candidate)
    fallback = electron_pkg / "dist" / "electron.exe"
    if fallback.is_file():
        return str(fallback)
    return None


class ElectronFixtureApp:
    """Launch and control naturo's *owned*, real Electron fixture app.

    Unlike :class:`ChromiumFixtureApp` (a browser standing in for the Electron
    content layer), this spins up an actual Electron main process from
    ``fixtures/electron/`` whose single :class:`BrowserWindow` renders varied
    interactive controls (toolbar buttons, text inputs, a tree, a task list, a
    data table).  The window is launched with a CDP remote-debugging endpoint,
    so the cascade's CDP provider enumerates the renderer DOM that the Windows
    UIA tree collapses into one opaque node.

    Because this is a genuine Electron process, the measured delta is the
    literal Electron case — not a representative proxy.

    Use as a context manager::

        with ElectronFixtureApp() as app:
            result = app.measure()
    """

    #: Window title set by ``fixtures/electron/main.js`` (used to find the HWND).
    WINDOW_TITLE_SUBSTRING = "Naturo Electron Recognition Fixture"

    def __init__(
        self,
        *,
        port: int = DEFAULT_ELECTRON_CDP_PORT,
        electron_path: Optional[str] = None,
    ) -> None:
        """Initialise the controller.

        Args:
            port: CDP remote-debugging port the Electron app should expose.
            electron_path: Override the auto-detected Electron executable.
        """
        self.app_dir = FIXTURES_DIR / "electron"
        self.port = port
        self.electron_path = electron_path or _resolve_electron_binary(self.app_dir)
        self._process: Optional[subprocess.Popen] = None
        self._user_data_dir: Optional[str] = None

    @property
    def available(self) -> bool:
        """Whether Electron is installed and the fixture sources are present."""
        return (
            self.electron_path is not None
            and (self.app_dir / "main.js").is_file()
            and (self.app_dir / "index.html").is_file()
        )

    def start(self, ready_timeout: float = 60.0) -> None:
        """Launch the Electron app and wait for both CDP and page load.

        Args:
            ready_timeout: Maximum seconds to wait for the CDP endpoint and a
                rendered renderer page.

        Raises:
            RuntimeError: If Electron is unavailable, or the CDP endpoint /
                renderer does not become ready within ``ready_timeout``.
        """
        import os
        import tempfile

        if not self.available or self.electron_path is None:
            raise RuntimeError(
                "Electron fixture unavailable: "
                f"electron={self.electron_path!r}, app_dir={self.app_dir!r}. "
                "Run `npm install` in benchmarks/recognition/fixtures/electron/."
            )

        self._user_data_dir = tempfile.mkdtemp(prefix="naturo_bench_electron_")
        env = dict(os.environ)
        env["NATURO_FIXTURE_CDP_PORT"] = str(self.port)
        env["NATURO_FIXTURE_USER_DATA_DIR"] = self._user_data_dir
        args: List[str] = [
            self.electron_path,
            str(self.app_dir),
            f"--remote-debugging-port={self.port}",
            "--remote-allow-origins=*",
        ]
        logger.info("Launching Electron fixture: %s", self.app_dir)
        self._process = subprocess.Popen(args, env=env)

        deadline = time.monotonic() + ready_timeout
        while time.monotonic() < deadline:
            if _port_is_open("127.0.0.1", self.port):
                break
            time.sleep(0.5)
        else:
            self.stop()
            raise RuntimeError(
                f"Electron CDP endpoint did not open on port {self.port} "
                f"within {ready_timeout:.0f}s."
            )

        if not self._wait_page_loaded(deadline):
            self.stop()
            raise RuntimeError("Electron renderer did not finish loading in time.")

    def _wait_page_loaded(self, deadline: float) -> bool:
        """Poll the CDP ``/json`` list until the renderer page is available.

        Args:
            deadline: ``time.monotonic()`` value after which to give up.

        Returns:
            ``True`` once the fixture's renderer is the active target, else
            ``False`` on timeout.
        """
        url = f"http://127.0.0.1:{self.port}/json"
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as response:
                    import json

                    targets = json.loads(response.read().decode("utf-8"))
                for target in targets:
                    if target.get("type") == "page" and "index.html" in target.get(
                        "url", ""
                    ):
                        time.sleep(1.0)  # settle the render
                        return True
            except (OSError, ValueError):
                pass
            time.sleep(0.5)
        return False

    def find_window(self):
        """Find the Electron fixture window via the backend.

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
        """Measure recognition coverage on the Electron fixture window.

        Args:
            depth: Maximum accessibility-tree depth to walk.

        Returns:
            A :class:`CoverageResult` for the owned Electron app.

        Raises:
            RuntimeError: If the fixture window cannot be found.
        """
        window = self.find_window()
        if window is None:
            raise RuntimeError(
                "Could not locate the Electron fixture window. "
                "Did the Electron app launch and render the fixture?"
            )
        return measure_window(
            app="Owned Electron fixture (real Electron app)",
            framework="Electron/CDP",
            hwnd=window.hwnd,
            pid=window.pid,
            depth=depth,
            notes=(
                "A real Electron process: the renderer's interactive controls "
                "(toolbar, inputs, tree, task list, table) live in the Chromium "
                "content layer that UIA collapses to one opaque node. Only the "
                "CDP provider recovers them — this is the literal Electron case, "
                "not a browser proxy."
            ),
        )

    def stop(self) -> None:
        """Terminate the Electron app and remove its throwaway profile."""
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

    def __enter__(self) -> "ElectronFixtureApp":
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.stop()


def _find_java_tool(tool: str) -> Optional[str]:
    """Locate a JDK tool (``java``/``javac``) via ``JAVA_HOME`` then ``PATH``.

    Args:
        tool: Bare tool name without extension (e.g. ``"javac"``).

    Returns:
        Absolute path to the executable, or ``None`` if it cannot be found.
    """
    import os
    import shutil

    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidate = Path(java_home) / "bin" / f"{tool}.exe"
        if candidate.is_file():
            return str(candidate)
        candidate = Path(java_home) / "bin" / tool
        if candidate.is_file():
            return str(candidate)
    return shutil.which(tool)


class JavaSwingFixtureApp:
    """Launch and control naturo's *owned* Java Swing recognition fixture.

    This compiles ``fixtures/java/SwingControlsFixture.java`` with ``javac`` (no
    Maven/Gradle) and runs it on the JVM.  The window's Swing controls
    (buttons, a text field, a checkbox, a label, a table and a tree) are
    invisible to the Windows UIA tree — which collapses the frame into opaque
    window chrome — but fully recovered by naturo's Java Access Bridge (JAB)
    provider.  The measured delta is therefore the literal Java/Swing case.

    Java Access Bridge must be enabled in the JVM (``jabswitch -enable``) and
    ``WindowsAccessBridge-64.dll`` must be on ``PATH`` (it ships in the JDK's
    ``bin`` directory) for the JAB provider to recognize the controls.

    Use as a context manager::

        with JavaSwingFixtureApp() as app:
            result = app.measure()
    """

    #: Window title set by ``SwingControlsFixture.java`` (used to find the HWND).
    WINDOW_TITLE_SUBSTRING = "Naturo Swing Recognition Fixture"
    #: Fully-qualified class name / source stem of the fixture.
    MAIN_CLASS = "SwingControlsFixture"

    def __init__(
        self,
        *,
        javac_path: Optional[str] = None,
        java_path: Optional[str] = None,
    ) -> None:
        """Initialise the controller.

        Args:
            javac_path: Override the auto-detected ``javac`` executable.
            java_path: Override the auto-detected ``java`` executable.
        """
        self.app_dir = FIXTURES_DIR / "java"
        self.source_path = self.app_dir / f"{self.MAIN_CLASS}.java"
        self.javac_path = javac_path or _find_java_tool("javac")
        self.java_path = java_path or _find_java_tool("java")
        self._process: Optional[subprocess.Popen] = None

    @property
    def available(self) -> bool:
        """Whether a JDK (``javac`` + ``java``) and the fixture source exist."""
        return (
            self.javac_path is not None
            and self.java_path is not None
            and self.source_path.is_file()
        )

    def _ensure_compiled(self) -> None:
        """Compile the fixture with ``javac`` if the class file is missing or stale.

        Raises:
            RuntimeError: If ``javac`` is unavailable or compilation fails.
        """
        if self.javac_path is None:
            raise RuntimeError("javac not found; install a JDK or set JAVA_HOME.")
        class_path = self.app_dir / f"{self.MAIN_CLASS}.class"
        if (
            class_path.is_file()
            and class_path.stat().st_mtime >= self.source_path.stat().st_mtime
        ):
            return
        logger.info("Compiling Java fixture: %s", self.source_path)
        result = subprocess.run(
            [self.javac_path, self.source_path.name],
            cwd=str(self.app_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"javac failed for {self.source_path}:\n{result.stderr}"
            )

    def start(self, ready_timeout: float = 30.0) -> None:
        """Compile, launch the Swing fixture, and wait for its window.

        Args:
            ready_timeout: Maximum seconds to wait for the fixture window to
                appear after launching the JVM.

        Raises:
            RuntimeError: If the JDK is unavailable, or the window does not
                appear within ``ready_timeout``.
        """
        if not self.available or self.java_path is None:
            raise RuntimeError(
                "Java Swing fixture unavailable: "
                f"javac={self.javac_path!r}, java={self.java_path!r}, "
                f"source={self.source_path!r}. Install a JDK (JAVA_HOME)."
            )

        self._ensure_compiled()
        logger.info("Launching Java Swing fixture: %s", self.MAIN_CLASS)
        self._process = subprocess.Popen(
            [self.java_path, self.MAIN_CLASS],
            cwd=str(self.app_dir),
        )

        deadline = time.monotonic() + ready_timeout
        while time.monotonic() < deadline:
            if self.find_window() is not None:
                time.sleep(1.0)  # settle the render and the JAB attach
                return
            if self._process.poll() is not None:
                self.stop()
                raise RuntimeError(
                    "Java fixture process exited before its window appeared."
                )
            time.sleep(0.5)
        self.stop()
        raise RuntimeError(
            f"Java Swing fixture window did not appear within {ready_timeout:.0f}s."
        )

    def find_window(self):
        """Find the Swing fixture window via the backend.

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
        """Measure recognition coverage on the Swing fixture window.

        Args:
            depth: Maximum accessibility-tree depth to walk.

        Returns:
            A :class:`CoverageResult` for the owned Java Swing app.

        Raises:
            RuntimeError: If the fixture window cannot be found.
        """
        window = self.find_window()
        if window is None:
            raise RuntimeError(
                "Could not locate the Java Swing fixture window. "
                "Did the JVM launch and render the fixture?"
            )
        return measure_window(
            app="Owned Java Swing fixture (real Swing app)",
            framework="Java Access Bridge",
            hwnd=window.hwnd,
            pid=window.pid,
            depth=depth,
            notes=(
                "A real Swing process: its buttons, text field, checkbox, "
                "label, table and tree live below a SunAwtFrame that the UIA "
                "tree collapses into opaque window chrome. Only the Java Access "
                "Bridge provider recovers them — the literal Java/Swing case. "
                "Requires JAB enabled and WindowsAccessBridge-64.dll on PATH."
            ),
        )

    def stop(self) -> None:
        """Terminate the JVM process."""
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

    def __enter__(self) -> "JavaSwingFixtureApp":
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.stop()


class ExcelComFixtureApp:
    """Launch and control an owned Excel workbook for COM-provider measurement.

    Excel collapses its cell grid into a single opaque UIA node; only the COM
    provider (binding the running Excel instance, cells projected via
    ``PointsToScreenPixels``) recovers the cells. This fixture writes a small
    known workbook, opens it in Excel, and measures the uia-only vs full-cascade
    delta — the literal spreadsheet case.
    """

    #: Excel window titles look like ``<file> - Excel``.
    WINDOW_TITLE_SUBSTRING = " - Excel"
    _STEM = "naturo_adaptation_cells"
    _CELLS = "Product,Qty\nWidget,42\nGadget,7\nSprocket,13\n"

    def __init__(self, *, excel_path: Optional[str] = None) -> None:
        import os

        self.excel_path = excel_path or os.path.join(
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            "Microsoft Office", "root", "Office16", "EXCEL.EXE",
        )
        self._process: Optional[subprocess.Popen] = None
        self._win_pid: Optional[int] = None
        self._workdir: Optional[str] = None

    @property
    def available(self) -> bool:
        import importlib.util

        return (
            Path(self.excel_path).is_file()
            and importlib.util.find_spec("win32com") is not None
        )

    def start(self, ready_timeout: float = 45.0) -> None:
        import os
        import tempfile

        if not self.available:
            raise RuntimeError(
                f"Excel COM fixture unavailable: excel={self.excel_path!r}; "
                "Excel + pywin32 required."
            )
        self._workdir = tempfile.mkdtemp(prefix="naturo_excel_fix_")
        csv_path = os.path.join(self._workdir, f"{self._STEM}.csv")
        with open(csv_path, "w", encoding="utf-8") as fh:
            fh.write(self._CELLS)
        logger.info("Launching Excel COM fixture: %s", csv_path)
        self._process = subprocess.Popen([self.excel_path, csv_path])

        deadline = time.monotonic() + ready_timeout
        while time.monotonic() < deadline:
            window = self.find_window()
            if window is not None:
                self._win_pid = window.pid  # the process actually hosting the grid
                time.sleep(2.5)  # settle render + Excel COM/ROT registration
                return
            time.sleep(0.5)
        self.stop()
        raise RuntimeError(
            f"Excel window did not appear within {ready_timeout:.0f}s."
        )

    def find_window(self):
        backend = get_backend()
        for window in backend.list_windows():
            title = window.title or ""
            if self.WINDOW_TITLE_SUBSTRING in title and self._STEM in title.lower():
                return window
        return None

    def measure(self, depth: int = 15) -> CoverageResult:
        window = self.find_window()
        if window is None:
            raise RuntimeError("Could not locate the Excel fixture window.")
        return measure_window(
            app="Owned Excel workbook (real Excel via COM)",
            framework="Excel COM",
            hwnd=window.hwnd,
            pid=window.pid,
            depth=depth,
            notes=(
                "A real Excel window: the cell grid is one opaque UIA node; only "
                "the COM provider (running-instance binding, cells projected via "
                "PointsToScreenPixels) recovers the cells."
            ),
        )

    def stop(self) -> None:
        # Kill Excel PID-scoped (the window's host process), then the launcher;
        # terminate — never a UI close — so no Save/Don't-Save dialog is raised.
        for pid in (self._win_pid, self._process.pid if self._process else None):
            if pid is None:
                continue
            try:
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    capture_output=True,
                )
            except OSError:
                pass
        self._process = None
        self._win_pid = None
        if self._workdir is not None:
            import shutil

            shutil.rmtree(self._workdir, ignore_errors=True)
            self._workdir = None

    def __enter__(self) -> "ExcelComFixtureApp":
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
