"""First-frame screenshot robustness tests (#1124).

The canonical first action an AI agent takes after ``browser launch`` is a
``browser screenshot`` — and against a freshly-launched **headless** Chrome the
first ``Page.captureScreenshot`` can stall until the compositor has produced an
on-screen frame, timing out the full CDP budget and writing no file. naturo's
verification model is "only trust screenshot evidence", so a 100%-on-first-try
failure there is release-blocking.

The fix (:meth:`naturo.browser._page.BrowserPage.screenshot`) enables the Page
domain before the first capture and retries the capture once on timeout, so a
transient first-frame stall self-heals instead of failing.

The unit tests below are hermetic — they drive a fake CDP transport, so they run
on the headless Linux/macOS CI matrix and deterministically prove the retry and
the Page-domain enable without needing a real first-frame race. The
``@pytest.mark.desktop`` test at the end is the integration guard: it launches a
real headless Chrome and asserts the very first capture writes a valid PNG.
"""
from __future__ import annotations

import base64
import socket
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from naturo.browser._page import BrowserPage
from naturo.cdp import CDPTimeoutError

# A minimal but structurally valid 1x1 PNG — what a real ``captureScreenshot``
# response carries (base64), so the success path writes a genuine PNG to disk.
_ONE_PX_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA"
    "60e6kgAAAABJRU5ErkJggg=="
)


class _FakeCDP:
    """Minimal stand-in for :class:`naturo.cdp.CDPClient`.

    Records every method sent and lets a test choose how many of the leading
    ``Page.captureScreenshot`` calls raise :class:`CDPTimeoutError` (simulating
    the headless first-frame stall) before one returns image data.
    """

    def __init__(self, capture_timeouts: int = 0) -> None:
        self.calls: List[str] = []
        self._remaining_timeouts = capture_timeouts
        self.capture_count = 0

    def send(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.calls.append(method)
        if method == "Page.captureScreenshot":
            self.capture_count += 1
            if self._remaining_timeouts > 0:
                self._remaining_timeouts -= 1
                raise CDPTimeoutError("simulated headless first-frame stall")
            return {"data": _ONE_PX_PNG_B64}
        return {}


def _page_with_fake_cdp(fake: _FakeCDP) -> BrowserPage:
    """Build a BrowserPage wired to *fake* without touching real Chrome.

    Bypasses ``__init__`` (which would connect over CDP) so the screenshot logic
    can be exercised against the fake transport in isolation.
    """
    page = BrowserPage.__new__(BrowserPage)
    page._cdp = fake  # type: ignore[attr-defined]
    return page


def test_screenshot_enables_page_domain_before_capture(tmp_path: Path) -> None:
    """The cold screenshot path enables the Page domain before capturing.

    A separately-connected ``screenshot`` process never navigates, so without an
    explicit ``Page.enable`` the compositor may never schedule the first frame
    (#1124).
    """
    fake = _FakeCDP(capture_timeouts=0)
    page = _page_with_fake_cdp(fake)

    out = page.screenshot(str(tmp_path / "shot.png"))

    assert "Page.enable" in fake.calls
    assert fake.calls.index("Page.enable") < fake.calls.index("Page.captureScreenshot")
    assert Path(out).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_screenshot_retries_once_on_first_frame_timeout(tmp_path: Path) -> None:
    """A first-capture timeout self-heals via exactly one retry (#1124)."""
    fake = _FakeCDP(capture_timeouts=1)
    page = _page_with_fake_cdp(fake)

    out = page.screenshot(str(tmp_path / "shot.png"))

    assert fake.capture_count == 2, "expected exactly one retry after the stall"
    assert Path(out).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_screenshot_no_retry_when_first_capture_succeeds(tmp_path: Path) -> None:
    """The happy path (modern headless) captures once — the retry is a net."""
    fake = _FakeCDP(capture_timeouts=0)
    page = _page_with_fake_cdp(fake)

    page.screenshot(str(tmp_path / "shot.png"))

    assert fake.capture_count == 1


def test_screenshot_retry_is_bounded(tmp_path: Path) -> None:
    """A persistently dead capture surfaces the timeout, not an infinite loop."""
    fake = _FakeCDP(capture_timeouts=99)
    page = _page_with_fake_cdp(fake)

    with pytest.raises(CDPTimeoutError):
        page.screenshot(str(tmp_path / "shot.png"))

    assert fake.capture_count == 2, "retry must be bounded to a single re-attempt"


# ── Integration guard (real headless Chrome) ─────────────────────────────────


def _free_tcp_port() -> int:
    """Return a currently-free loopback TCP port for the CDP endpoint."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.desktop
def test_first_screenshot_after_headless_launch_writes_png(tmp_path: Path) -> None:
    """The very first capture against a fresh headless Chrome writes a PNG.

    Faithful to the #1124 repro: ``browser launch --url`` loads content in one
    connection, then a *separate* cold connection (the ``browser screenshot``
    process) takes the first capture against the Chrome instance. That first
    capture must write a valid PNG and not raise — no warm-up screenshot
    required.
    """
    import shutil

    from naturo.browser import launch_chrome

    fixture = (Path(__file__).parent / "fixtures" / "basic.html").resolve().as_uri()
    user_data_dir = tempfile.mkdtemp(prefix="naturo_first_frame_")
    port = _free_tcp_port()
    chrome = launch_chrome(
        port=port,
        headless=True,
        user_data_dir=user_data_dir,
        timeout=30.0,
    )
    try:
        # Load content the way ``browser launch --url`` does, then drop the
        # connection — navigating does not warm the compositor (only a capture
        # does), so the next connection's first capture is the cold path.
        loader = BrowserPage(port=port)
        loader.navigate(fixture)
        loader.close()

        # A fresh cold connection: this first capture is the #1124 scenario.
        page = BrowserPage(port=port)
        try:
            out = page.screenshot(str(tmp_path / "first.png"))
        finally:
            page.close()

        data = Path(out).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n", "first capture wrote a non-PNG"
        assert data[12:16] == b"IHDR", "first capture wrote a truncated PNG"
    finally:
        chrome.terminate()
        try:
            chrome.wait(timeout=10)
        except subprocess.TimeoutExpired:
            chrome.kill()
        shutil.rmtree(user_data_dir, ignore_errors=True)
