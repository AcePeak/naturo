"""File download management for browser automation.

Configures Chrome to download files to a specific directory and
provides a polling-based mechanism to wait for downloads to complete.

Usage (programmatic)::

    from naturo.browser import BrowserPage
    from naturo.browser._download import set_download_dir, wait_for_download

    page = BrowserPage(port=9222)
    set_download_dir(page, "/tmp/downloads")
    page.find("a.download-link").click()
    path = wait_for_download("/tmp/downloads", timeout=60)
    print(f"Downloaded: {path}")

Usage (CLI)::

    naturo browser download --dir /tmp/downloads
    naturo browser download --dir /tmp/downloads --wait --timeout 60
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Chrome uses these extensions for partial downloads
_PARTIAL_EXTENSIONS = frozenset({".crdownload", ".tmp", ".download", ".part"})


@dataclass(frozen=True)
class DownloadResult:
    """A completed browser download.

    Returned by :meth:`naturo.browser.BrowserPage.wait_for_download`. The
    ``path`` attribute is the documented surface (see the migration guide's
    *File Download* section); ``name`` and ``size`` are convenience accessors.
    """

    path: str

    @property
    def name(self) -> str:
        """The downloaded file's basename, e.g. ``report.txt``."""
        return os.path.basename(self.path)

    @property
    def size(self) -> int:
        """The downloaded file's size in bytes."""
        return os.path.getsize(self.path)


def set_download_dir(page, directory: str) -> None:
    """Configure the browser to save downloads to a specific directory.

    Uses ``Browser.setDownloadBehavior`` CDP command to tell Chrome
    where to save files and to allow downloads without prompts.

    Args:
        page: A :class:`~naturo.browser.BrowserPage` instance.
        directory: Absolute path to the download directory.

    Raises:
        ValueError: If directory does not exist.
        CDPError: If the CDP command fails.
    """
    abs_dir = os.path.abspath(directory)
    if not os.path.isdir(abs_dir):
        raise ValueError(f"Download directory does not exist: {abs_dir}")

    page._cdp.send(
        "Browser.setDownloadBehavior",
        {
            "behavior": "allow",
            "downloadPath": abs_dir,
        },
    )
    logger.info("Download directory set to: %s", abs_dir)


def wait_for_download(
    directory: str,
    timeout: float = 60.0,
    poll_interval: float = 0.5,
) -> str:
    """Wait for a file download to complete in the given directory.

    Monitors the directory for new files and waits until no partial
    download files (``.crdownload``, ``.tmp``, ``.part``) remain.
    Returns the path to the most recently completed download.

    Args:
        directory: Directory where Chrome saves downloads.
        timeout: Maximum seconds to wait (default 60).
        poll_interval: Seconds between directory polls (default 0.5).

    Returns:
        Absolute path to the downloaded file.

    Raises:
        TimeoutError: If download does not complete within timeout.
        ValueError: If directory does not exist.
    """
    abs_dir = os.path.abspath(directory)
    if not os.path.isdir(abs_dir):
        raise ValueError(f"Download directory does not exist: {abs_dir}")

    # Snapshot existing files to detect new ones
    before = _list_files(abs_dir)
    deadline = time.monotonic() + timeout

    # Phase 1: wait for a new file to appear (partial or complete)
    while time.monotonic() < deadline:
        current = _list_files(abs_dir)
        new_files = current - before
        if new_files:
            break
        time.sleep(poll_interval)
    else:
        raise TimeoutError(
            f"No new file appeared in {abs_dir} within {timeout}s"
        )

    # Phase 2: wait for partial downloads to finish
    while time.monotonic() < deadline:
        current = _list_files(abs_dir)
        partials = {f for f in current if _is_partial(f)}
        if not partials:
            # Find the newest completed file
            completed = current - before
            # Remove partials from completed set
            completed = {f for f in completed if not _is_partial(f)}
            if completed:
                newest = max(
                    completed,
                    key=lambda f: os.path.getmtime(os.path.join(abs_dir, f)),
                )
                result = os.path.join(abs_dir, newest)
                logger.info("Download complete: %s", result)
                return result
        time.sleep(poll_interval)

    raise TimeoutError(
        f"Download did not complete in {abs_dir} within {timeout}s"
    )


def _list_files(directory: str) -> set:
    """List files (not directories) in a directory.

    Args:
        directory: Path to scan.

    Returns:
        Set of filenames.
    """
    try:
        return {
            f for f in os.listdir(directory)
            if os.path.isfile(os.path.join(directory, f))
        }
    except OSError:
        return set()


def _is_partial(filename: str) -> bool:
    """Check if a filename looks like a partial download.

    Args:
        filename: The filename to check.

    Returns:
        True if the file has a partial-download extension.
    """
    _, ext = os.path.splitext(filename)
    return ext.lower() in _PARTIAL_EXTENSIONS
