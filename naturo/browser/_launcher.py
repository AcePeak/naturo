"""Chrome launcher with profile support for browser automation.

Finds and launches Chrome/Chromium/Edge with ``--remote-debugging-port``
enabled, optionally using a specific user profile or temporary profile.

Usage (programmatic)::

    from naturo.browser._launcher import (
        find_chrome,
        launch_chrome,
        list_profiles,
    )

    # Launch with default profile
    proc = launch_chrome(port=9222)

    # Launch with a named profile
    proc = launch_chrome(port=9222, profile="Work")

    # Launch with a custom user data directory
    proc = launch_chrome(port=9222, user_data_dir="/path/to/profile")

    # List available Chrome profiles
    profiles = list_profiles()

Usage (CLI)::

    naturo browser launch
    naturo browser launch --profile Work
    naturo browser launch --user-data-dir /path/to/profile
    naturo browser profiles
"""

from __future__ import annotations

import json as json_module
import logging
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

# ── Chrome binary discovery ─────────────────────────────────────────────────

_CHROME_NAMES_WINDOWS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

_CHROME_NAMES_MACOS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]

_CHROME_NAMES_LINUX = [
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
]


def find_chrome() -> Optional[str]:
    """Find the Chrome/Chromium/Edge binary on the system.

    Searches platform-specific default locations and the system PATH.

    Returns:
        Absolute path to the browser executable, or ``None`` if not found.
    """
    system = platform.system()

    if system == "Windows":
        for path in _CHROME_NAMES_WINDOWS:
            expanded = os.path.expandvars(path)
            if os.path.isfile(expanded):
                return expanded
    elif system == "Darwin":
        for path in _CHROME_NAMES_MACOS:
            if os.path.isfile(path):
                return path
    else:
        # Linux — check PATH via shutil.which
        import shutil
        for name in _CHROME_NAMES_LINUX:
            found = shutil.which(name)
            if found:
                return found

    return None


# ── Profile discovery ────────────────────────────────────────────────────────


def _default_user_data_dir() -> Optional[Path]:
    """Return the default Chrome user data directory for the current OS.

    Returns:
        Path to the user data directory, or ``None`` if unknown.
    """
    system = platform.system()
    home = Path.home()

    if system == "Windows":
        local_app = os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local"))
        return Path(local_app) / "Google" / "Chrome" / "User Data"
    elif system == "Darwin":
        return home / "Library" / "Application Support" / "Google" / "Chrome"
    else:
        return home / ".config" / "google-chrome"


def list_profiles(user_data_dir: Optional[str] = None) -> List[Dict[str, str]]:
    """List available Chrome profiles.

    Reads the ``Local State`` file and each profile's ``Preferences`` to
    extract profile names and directories.

    Args:
        user_data_dir: Path to the Chrome user data directory.
            If ``None``, uses the OS default.

    Returns:
        List of dicts with keys: ``directory``, ``name``, ``path``.
        Empty list if no profiles found or directory doesn't exist.
    """
    data_dir: Path
    if user_data_dir:
        data_dir = Path(user_data_dir)
    else:
        resolved = _default_user_data_dir()
        if resolved is None:
            return []
        data_dir = resolved

    local_state = data_dir / "Local State"
    if not local_state.is_file():
        return []

    try:
        with open(local_state, encoding="utf-8") as f:
            state = json_module.load(f)
    except (OSError, json_module.JSONDecodeError) as exc:
        logger.debug("Cannot read Local State: %s", exc)
        return []

    profile_info = state.get("profile", {}).get("info_cache", {})
    profiles: List[Dict[str, str]] = []

    for dir_name, info in sorted(profile_info.items()):
        profile_path = data_dir / dir_name
        if profile_path.is_dir():
            profiles.append({
                "directory": dir_name,
                "name": info.get("name", dir_name),
                "path": str(profile_path),
            })

    return profiles


def _resolve_profile_directory(
    profile: str,
    user_data_dir: Optional[str] = None,
) -> Optional[str]:
    """Resolve a profile name or directory to the actual directory name.

    Accepts either the profile display name (e.g. "Work") or the
    directory name (e.g. "Profile 1"). Returns the directory name
    suitable for ``--profile-directory``.

    Args:
        profile: Profile name or directory name.
        user_data_dir: Optional user data directory override.

    Returns:
        The Chrome profile directory name, or ``None`` if not found.
    """
    profiles = list_profiles(user_data_dir)

    for p in profiles:
        if p["directory"] == profile or p["name"] == profile:
            return p["directory"]

    return None


# ── Chrome launcher ──────────────────────────────────────────────────────────


class ChromeProcess:
    """Handle to a launched Chrome process.

    Attributes:
        port: The CDP debugging port.
        pid: The OS process ID.
        process: The underlying :class:`subprocess.Popen` object.
    """

    def __init__(
        self,
        process: subprocess.Popen,  # type: ignore[type-arg]
        port: int,
    ) -> None:
        self.process = process
        self.port = port
        self.pid = process.pid

    def is_running(self) -> bool:
        """Check if the Chrome process is still running.

        Returns:
            ``True`` if the process has not exited.
        """
        return self.process.poll() is None

    def terminate(self) -> None:
        """Terminate the Chrome process gracefully."""
        if self.is_running():
            self.process.terminate()

    def kill(self) -> None:
        """Force-kill the Chrome process."""
        if self.is_running():
            self.process.kill()

    def wait(self, timeout: Optional[float] = None) -> int:
        """Wait for the Chrome process to exit.

        Args:
            timeout: Maximum seconds to wait (``None`` = forever).

        Returns:
            The process exit code.
        """
        return self.process.wait(timeout=timeout)

    def __repr__(self) -> str:
        status = "running" if self.is_running() else "stopped"
        return f"ChromeProcess(pid={self.pid}, port={self.port}, {status})"


def launch_chrome(
    port: int = 9222,
    headless: bool = False,
    profile: Optional[str] = None,
    user_data_dir: Optional[str] = None,
    extra_args: Optional[Sequence[str]] = None,
    url: Optional[str] = None,
    chrome_path: Optional[str] = None,
    wait_ready: bool = True,
    timeout: float = 15.0,
) -> ChromeProcess:
    """Launch Chrome with remote debugging enabled.

    Args:
        port: CDP debugging port (default 9222).
        headless: Run in headless mode.
        profile: Chrome profile name or directory (e.g. "Work", "Profile 1").
            Resolved against the user data directory.
        user_data_dir: Custom user data directory. Overrides the default
            Chrome profile location entirely.
        extra_args: Additional Chrome command-line flags.
        url: Initial URL to open (default: ``about:blank``).
        chrome_path: Explicit path to Chrome binary. If ``None``,
            auto-detected via :func:`find_chrome`.
        wait_ready: Wait for the CDP endpoint to become available.
        timeout: Seconds to wait for CDP readiness (default 15).

    Returns:
        A :class:`ChromeProcess` handle.

    Raises:
        FileNotFoundError: If Chrome binary cannot be found.
        RuntimeError: If Chrome fails to start or CDP is not ready
            within the timeout.
    """
    if chrome_path is None:
        chrome_path = find_chrome()
    if chrome_path is None:
        raise FileNotFoundError(
            "Chrome/Chromium/Edge not found. Install Chrome or pass "
            "--chrome-path to specify the browser location."
        )

    args = [
        chrome_path,
        f"--remote-debugging-port={port}",
    ]

    if headless:
        args.append("--headless=new")

    # Profile handling
    if user_data_dir:
        args.append(f"--user-data-dir={user_data_dir}")
        if profile:
            # When user_data_dir is explicit, use profile as-is
            args.append(f"--profile-directory={profile}")
    elif profile:
        # Resolve profile name to directory
        resolved = _resolve_profile_directory(profile)
        if resolved:
            args.append(f"--profile-directory={resolved}")
        else:
            # Use as literal directory name (e.g., "Default", "Profile 1")
            args.append(f"--profile-directory={profile}")

    if extra_args:
        args.extend(extra_args)

    args.append(url or "about:blank")

    logger.info("Launching Chrome: %s", " ".join(args))

    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        raise FileNotFoundError(
            f"Failed to launch Chrome at {chrome_path}: {exc}"
        ) from exc

    chrome = ChromeProcess(proc, port)

    if wait_ready:
        _wait_for_cdp(port, timeout=timeout, process=proc)

    return chrome


def _wait_for_cdp(
    port: int,
    timeout: float = 15.0,
    process: Optional[subprocess.Popen] = None,  # type: ignore[type-arg]
) -> None:
    """Wait for the CDP HTTP endpoint to become available.

    Args:
        port: CDP port to poll.
        timeout: Maximum seconds to wait.
        process: Optional process to check for early exit.

    Raises:
        RuntimeError: If CDP is not ready within timeout or process exits.
    """
    import urllib.request
    import urllib.error

    deadline = time.monotonic() + timeout
    url = f"http://localhost:{port}/json/version"

    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(
                f"Chrome exited with code {process.returncode} "
                "before CDP became available"
            )
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2):
                return  # CDP is ready
        except (urllib.error.URLError, OSError):
            time.sleep(0.3)

    raise RuntimeError(
        f"Chrome CDP endpoint not ready at port {port} "
        f"after {timeout:.0f}s. Is the port already in use?"
    )
