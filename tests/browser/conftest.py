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
import threading
from pathlib import Path
from typing import Iterator

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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
