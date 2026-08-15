"""Shared fixtures for the browser migration acceptance suite (#766).

The migration matrix (#766/#1063) compares *Before* (DrissionPage/Selenium/
pywinauto) against *After* (naturo) on deterministic, fully-offline pages.
This module provides the local HTTP server those tests serve the fixtures
from — the exact same serving model #1063 will point Chrome at, so any
fixture that loads here is guaranteed loadable there.
"""

from __future__ import annotations

import functools
import http.server
import shutil
import socket
import tempfile
import threading
from pathlib import Path
from typing import Iterator

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _free_tcp_port() -> int:
    """Return a currently-free loopback TCP port for the CDP endpoint."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def naturo_browser() -> Iterator["object"]:
    """Launch a headless browser via naturo with GUARANTEED teardown (#1202).

    Every browser test that needs a real browser must take this fixture instead
    of calling ``launch_chrome`` / ``naturo browser launch`` raw. It:

    * launches headless Chrome in its **own throwaway ``user_data_dir`` on a free
      debug port**, so it never touches the real Chrome profile and concurrent
      desktop runs (Dev + QA) never share a profile;
    * **registers the launched PID** with the session-end safety-net sweeper
      (``tests._teardown_registry``), so a crash before this fixture's own
      teardown still gets the browser reaped; and
    * in ``finally`` (runs even when the test fails/raises) **quits then
      hard-kills the tracked PID and its child tree** via ``kill_pid``
      (``taskkill /F /T``) — force-close so a beforeunload/prompt cannot strand
      it — and removes the temp profile dir.

    Teardown is strictly PID-scoped: it only ever kills the exact PID this
    fixture launched, never by image name, so the human's real Chrome/Edge
    windows are untouched.

    Yields:
        The :class:`naturo.browser.ChromeProcess` handle. ``.port`` is the CDP
        port — build a ``BrowserPage(port=browser.port)`` to drive it.
    """
    from naturo.browser import launch_chrome
    from tests._launch import kill_pid
    from tests._teardown_registry import register

    user_data_dir = tempfile.mkdtemp(prefix="naturo_browser_1202_")
    port = _free_tcp_port()
    chrome = launch_chrome(
        port=port,
        headless=True,
        user_data_dir=user_data_dir,
        timeout=30.0,
    )
    register(chrome.pid)
    try:
        yield chrome
    finally:
        try:
            chrome.terminate()
            chrome.wait(timeout=10)
        except Exception:
            pass
        # Hard-kill the tracked PID + its Chrome child tree, PID-scoped only.
        kill_pid(chrome.pid)
        shutil.rmtree(user_data_dir, ignore_errors=True)


class _QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Static-file handler that does not spam stderr with per-request logs."""

    def log_message(self, *args: object) -> None:  # noqa: D102 - silence logging
        pass


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Absolute path to ``tests/browser/fixtures``."""
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def fixtures_server() -> Iterator[str]:
    """Serve the fixtures directory over loopback HTTP for the test session.

    Binds to port 0 so the OS assigns a free port (no collisions when CI runs
    suites in parallel). Yields the base URL, e.g. ``http://127.0.0.1:54321``.
    """
    handler = functools.partial(_QuietHTTPRequestHandler, directory=str(FIXTURES_DIR))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    # Host is the loopback literal we bound to; only the OS-assigned port varies.
    port = server.server_address[1]
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
