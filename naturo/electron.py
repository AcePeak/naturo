"""Electron and CEF application detection and automation support.

Provides utilities to detect Electron/CEF-based applications, discover
existing DevTools ports, and launch Electron apps with remote debugging
enabled for CDP-based DOM automation.

Phase 5C.4 — Electron/CEF App Support.

Usage::

    from naturo.electron import detect_electron_app, get_debug_port
    from naturo.cdp import CDPClient

    info = detect_electron_app("Slack")
    if info["is_electron"]:
        port = info.get("debug_port")
        if port:
            client = CDPClient(port=port)
            tabs = client.list_tabs()
"""

from __future__ import annotations

import os
import platform
import re
import subprocess
from typing import Any, Dict, List, Optional

from naturo.errors import NaturoError


# Known Electron-based applications and their typical executable names
_KNOWN_ELECTRON_APPS: Dict[str, Dict[str, Any]] = {
    "slack": {"exe": "Slack.exe", "display": "Slack"},
    "discord": {"exe": "Discord.exe", "display": "Discord"},
    "vscode": {"exe": "Code.exe", "display": "Visual Studio Code"},
    "code": {"exe": "Code.exe", "display": "Visual Studio Code"},
    "teams": {"exe": "ms-teams.exe", "display": "Microsoft Teams"},
    "notion": {"exe": "Notion.exe", "display": "Notion"},
    "figma": {"exe": "Figma.exe", "display": "Figma"},
    "obsidian": {"exe": "Obsidian.exe", "display": "Obsidian"},
    "postman": {"exe": "Postman.exe", "display": "Postman"},
    "spotify": {"exe": "Spotify.exe", "display": "Spotify"},
    "whatsapp": {"exe": "WhatsApp.exe", "display": "WhatsApp"},
    "telegram": {"exe": "Telegram.exe", "display": "Telegram Desktop"},
    "signal": {"exe": "Signal.exe", "display": "Signal"},
    "1password": {"exe": "1Password.exe", "display": "1Password"},
    "bitwarden": {"exe": "Bitwarden.exe", "display": "Bitwarden"},
    "cursor": {"exe": "Cursor.exe", "display": "Cursor"},
    "windsurf": {"exe": "Windsurf.exe", "display": "Windsurf"},
    "feishu": {"exe": "Feishu.exe", "display": "Feishu"},
    "lark": {"exe": "Lark.exe", "display": "Lark"},
    "dingtalk": {"exe": "DingTalk.exe", "display": "DingTalk"},
    "wechat-devtools": {"exe": "wechatdevtools.exe", "display": "WeChat DevTools"},
    "typora": {"exe": "Typora.exe", "display": "Typora"},
}


def _require_windows() -> None:
    """Raise NaturoError if not running on Windows.

    Raises:
        NaturoError: If the current platform is not Windows.
    """
    if platform.system() != "Windows":
        raise NaturoError(
            code="PLATFORM_ERROR",
            message="Electron detection requires Windows.",
        )


def _get_process_command_line(pid: int) -> Optional[str]:
    """Get the full command line of a process by PID.

    Args:
        pid: Process ID.

    Returns:
        Full command line string, or None if inaccessible.
    """
    try:
        result = subprocess.run(
            [
                "wmic",
                "process",
                "where",
                f"ProcessId={pid}",
                "get",
                "CommandLine",
                "/format:list",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if line.startswith("CommandLine="):
                return line[len("CommandLine=") :]
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def _get_process_exe_path(pid: int) -> Optional[str]:
    """Get the executable path of a process by PID.

    Args:
        pid: Process ID.

    Returns:
        Executable path string, or None if inaccessible.
    """
    try:
        result = subprocess.run(
            [
                "wmic",
                "process",
                "where",
                f"ProcessId={pid}",
                "get",
                "ExecutablePath",
                "/format:list",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.splitlines():
            if line.startswith("ExecutablePath="):
                return line[len("ExecutablePath=") :]
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def _bulk_get_process_info() -> Dict[int, Dict[str, str]]:
    """Batch-fetch CommandLine and ExecutablePath for all processes.

    Uses a single ``wmic`` call to retrieve info for every process at once,
    avoiding per-PID subprocess overhead that causes ``electron list`` to hang.

    Returns:
        Dict mapping PID to {command_line: str, exe_path: str}.
    """
    info: Dict[int, Dict[str, str]] = {}
    try:
        result = subprocess.run(
            [
                "wmic",
                "process",
                "get",
                "ProcessId,CommandLine,ExecutablePath",
                "/format:csv",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        lines = result.stdout.strip().splitlines()
        # CSV header line: Node,CommandLine,ExecutablePath,ProcessId
        header_idx = -1
        for i, line in enumerate(lines):
            if "ProcessId" in line and "CommandLine" in line:
                header_idx = i
                break
        if header_idx < 0:
            return info
        headers = [h.strip() for h in lines[header_idx].split(",")]
        try:
            pid_col = headers.index("ProcessId")
            cmd_col = headers.index("CommandLine")
            exe_col = headers.index("ExecutablePath")
        except ValueError:
            return info

        for line in lines[header_idx + 1 :]:
            parts = line.split(",")
            if len(parts) <= max(pid_col, cmd_col, exe_col):
                continue
            try:
                pid = int(parts[pid_col].strip())
            except (ValueError, IndexError):
                continue
            info[pid] = {
                "command_line": parts[cmd_col].strip(),
                "exe_path": parts[exe_col].strip(),
            }
    except (subprocess.TimeoutExpired, OSError):
        pass
    return info


def _find_processes_by_name(name: str) -> List[Dict[str, Any]]:
    """Find running processes matching a name pattern.

    Args:
        name: Process name or partial match (case-insensitive).

    Returns:
        List of dicts with pid, name, exe_path, command_line.
    """
    processes: List[Dict[str, Any]] = []
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        name_lower = name.lower()
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            # CSV format: "Image Name","PID","Session Name","Session#","Mem Usage"
            parts = line.split('","')
            if len(parts) < 2:
                continue
            proc_name = parts[0].strip('"')
            try:
                pid = int(parts[1].strip('"'))
            except (ValueError, IndexError):
                continue
            if name_lower in proc_name.lower():
                processes.append({
                    "pid": pid,
                    "name": proc_name,
                })
    except (subprocess.TimeoutExpired, OSError):
        pass
    return processes


def _is_electron_process(
    pid: int,
    proc_info: Optional[Dict[int, Dict[str, str]]] = None,
) -> bool:
    """Check if a process is an Electron/CEF application.

    Checks for Electron-specific files adjacent to the executable
    or Electron-specific command line arguments.

    Args:
        pid: Process ID to check.
        proc_info: Optional pre-fetched bulk process info from
            ``_bulk_get_process_info()``.  When provided, avoids
            per-PID ``wmic`` calls.

    Returns:
        True if the process appears to be Electron-based.
    """
    # Resolve command line and exe path, preferring bulk data
    if proc_info and pid in proc_info:
        cmdline = proc_info[pid].get("command_line") or None
        exe_path = proc_info[pid].get("exe_path") or None
    else:
        cmdline = _get_process_command_line(pid)
        exe_path = _get_process_exe_path(pid)

    # Check command line for Electron indicators
    if cmdline:
        electron_indicators = [
            "--type=renderer",
            "--type=gpu-process",
            "--type=utility",
            "electron",
            "resources/app.asar",
            "resources\\app.asar",
        ]
        cmdline_lower = cmdline.lower()
        if any(ind in cmdline_lower for ind in electron_indicators):
            return True

    # Check for Electron files next to the executable
    if exe_path:
        exe_dir = os.path.dirname(exe_path)
        electron_files = [
            "resources/app.asar",
            "resources\\app.asar",
            "electron.exe",
            "chrome_100_percent.pak",
            "icudtl.dat",
            "v8_context_snapshot.bin",
        ]
        for ef in electron_files:
            if os.path.exists(os.path.join(exe_dir, ef)):
                return True

    return False


def _find_debug_port_from_cmdline(
    pid: int,
    proc_info: Optional[Dict[int, Dict[str, str]]] = None,
) -> Optional[int]:
    """Extract --remote-debugging-port from a process command line.

    Args:
        pid: Process ID.
        proc_info: Optional pre-fetched bulk process info from
            ``_bulk_get_process_info()``.

    Returns:
        Port number if found, None otherwise.
    """
    if proc_info and pid in proc_info:
        cmdline = proc_info[pid].get("command_line") or None
    else:
        cmdline = _get_process_command_line(pid)
    if cmdline:
        match = re.search(r"--remote-debugging-port=(\d+)", cmdline)
        if match:
            return int(match.group(1))
    return None


def detect_electron_app(app_name: str) -> Dict[str, Any]:
    """Detect if a running application is Electron-based.

    Searches for processes matching the app name and checks for
    Electron/CEF characteristics.

    Args:
        app_name: Application name or process name to search for.

    Returns:
        Dict with keys:
            - is_electron: bool
            - app_name: str (display name)
            - processes: list of matching process dicts
            - debug_port: int or None (if already running with CDP)
            - main_pid: int or None (main process PID)

    Raises:
        NaturoError: If not on Windows or app not found.
    """
    _require_windows()

    # Normalize name for lookup
    name_lower = app_name.lower().replace(".exe", "")

    # Check known apps for the exe name
    known = _KNOWN_ELECTRON_APPS.get(name_lower)
    search_name = known["exe"] if known else app_name

    processes = _find_processes_by_name(search_name)
    if not processes:
        # Try the raw name too
        processes = _find_processes_by_name(app_name)

    if not processes:
        return {
            "is_electron": False,
            "app_name": app_name,
            "processes": [],
            "debug_port": None,
            "main_pid": None,
        }

    # Check each process for Electron characteristics
    is_electron = False
    debug_port = None
    main_pid = None

    for proc in processes:
        pid = proc["pid"]
        if _is_electron_process(pid):
            is_electron = True
            if main_pid is None:
                main_pid = pid
            port = _find_debug_port_from_cmdline(pid)
            if port is not None:
                debug_port = port
                break

    display_name = known["display"] if known else app_name

    return {
        "is_electron": is_electron,
        "app_name": display_name,
        "processes": processes,
        "debug_port": debug_port,
        "main_pid": main_pid,
    }


def _get_display_name(exe_name: str) -> str:
    """Map executable name to a friendly display name.

    Args:
        exe_name: Executable filename (e.g. 'Feishu.exe').

    Returns:
        Display name from known apps, or exe name without extension.
    """
    name_lower = exe_name.lower().replace(".exe", "")
    known = _KNOWN_ELECTRON_APPS.get(name_lower)
    if known:
        return known["display"]
    # Strip .exe and capitalize
    return exe_name.replace(".exe", "").replace(".EXE", "")


def list_electron_apps() -> Dict[str, Any]:
    """List all detected Electron/CEF applications currently running.

    Scans ALL running processes and checks each for Electron/CEF
    characteristics (resources/app.asar, electron indicators in
    command line, etc.). The known apps list is only used for
    display name mapping.

    Returns:
        Dict with keys:
            - apps: list of dicts with app_name, pid, debug_port, exe_name
            - count: int
    """
    _require_windows()

    apps: List[Dict[str, Any]] = []

    # Get all running processes
    try:
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return {"apps": [], "count": 0}

    # Group processes by executable name
    exe_groups: Dict[str, List[int]] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split('","')
        if len(parts) < 2:
            continue
        proc_name = parts[0].strip('"')
        try:
            pid = int(parts[1].strip('"'))
        except (ValueError, IndexError):
            continue
        # Skip system/common non-Electron processes
        skip = {
            "system", "system idle process", "registry", "smss.exe",
            "csrss.exe", "wininit.exe", "services.exe", "lsass.exe",
            "svchost.exe", "fontdrvhost.exe", "dwm.exe", "explorer.exe",
            "tasklist.exe", "conhost.exe", "cmd.exe", "powershell.exe",
            "pwsh.exe", "wmic.exe", "taskhostw.exe", "sihost.exe",
            "ctfmon.exe", "dllhost.exe", "mmc.exe", "searchhost.exe",
            "runtimebroker.exe", "applicationframehost.exe",
            "textinputhost.exe", "widgetservice.exe", "securityhealthtray.exe",
            "securityhealthservice.exe", "sgrmbroker.exe", "spoolsv.exe",
            "openssh-server.exe", "sshd.exe", "tail.exe", "python.exe",
            "python3.exe", "node.exe", "java.exe", "javaw.exe",
        }
        if proc_name.lower() in skip:
            continue
        if proc_name not in exe_groups:
            exe_groups[proc_name] = []
        exe_groups[proc_name].append(pid)

    # Bulk-fetch command lines and exe paths in a single wmic call
    # to avoid per-PID subprocess overhead that caused hanging (BUG-007).
    proc_info = _bulk_get_process_info()

    # Check each unique exe for Electron characteristics
    # Must check ALL pids for an exe because the main process often
    # has no Electron indicators — only child processes (renderer,
    # gpu-process, utility) do. Apps like Feishu use a custom framework
    # layer, so main process lacks app.asar and Electron markers.
    for exe_name, pids in exe_groups.items():
        found = False
        main_pid = pids[0]  # First PID is typically the main process
        debug_port = None
        for pid in pids:
            if _is_electron_process(pid, proc_info=proc_info):
                found = True
                port = _find_debug_port_from_cmdline(pid, proc_info=proc_info)
                if port is not None:
                    debug_port = port
                break  # One Electron child is enough to confirm
        if found:
            # Also check main process for debug port
            if debug_port is None:
                debug_port = _find_debug_port_from_cmdline(
                    main_pid, proc_info=proc_info,
                )
            display_name = _get_display_name(exe_name)
            apps.append({
                "app_name": display_name,
                "exe_name": exe_name,
                "pid": main_pid,
                "debug_port": debug_port,
                "debuggable": debug_port is not None,
                "process_count": len(pids),
            })

    return {"apps": apps, "count": len(apps)}


def get_debug_port(app_name: str) -> Optional[int]:
    """Get the DevTools debugging port of a running Electron app.

    Args:
        app_name: Application name to check.

    Returns:
        Port number if the app is running with remote debugging,
        None otherwise.
    """
    info = detect_electron_app(app_name)
    return info.get("debug_port")


def launch_with_debug(
    app_path: str,
    port: int = 9229,
    extra_args: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Launch an Electron app with remote debugging enabled.

    Starts the application with ``--remote-debugging-port`` so it can
    be controlled via CDP.

    Args:
        app_path: Full path to the Electron app executable.
        port: DevTools port (default 9229, avoids conflict with Chrome 9222).
        extra_args: Additional command line arguments.

    Returns:
        Dict with pid, port, and app_path.

    Raises:
        NaturoError: If launch fails or path doesn't exist.
    """
    _require_windows()

    if not os.path.isfile(app_path):
        raise NaturoError(
            code="FILE_NOT_FOUND",
            message=f"Executable not found: {app_path}",
        )

    args = [app_path, f"--remote-debugging-port={port}"]
    if extra_args:
        args.extend(extra_args)

    try:
        proc = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=0x00000008,  # DETACHED_PROCESS on Windows
        )
        return {
            "pid": proc.pid,
            "port": port,
            "app_path": app_path,
        }
    except OSError as exc:
        raise NaturoError(
            code="LAUNCH_FAILED",
            message=f"Failed to launch {app_path}: {exc}",
        ) from exc


def connect_to_electron(
    app_name: str,
    port: Optional[int] = None,
) -> Dict[str, Any]:
    """Connect to a running Electron app via CDP.

    Detects if the app is running with a debug port. If ``port`` is
    specified, tries that port directly.

    Args:
        app_name: Application name.
        port: Specific port to try (overrides auto-detection).

    Returns:
        Dict with success, port, tabs list.

    Raises:
        NaturoError: If app not found or not debuggable.
    """
    _require_windows()

    if port is None:
        info = detect_electron_app(app_name)
        if not info["is_electron"]:
            raise NaturoError(
                code="NOT_ELECTRON",
                message=(
                    f"'{app_name}' is not an Electron application "
                    "or is not currently running."
                ),
            )
        port = info.get("debug_port")
        if port is None:
            raise NaturoError(
                code="NO_DEBUG_PORT",
                message=(
                    f"'{app_name}' is running but not with remote debugging. "
                    f"Restart it with --remote-debugging-port=<port> to enable "
                    f"CDP access."
                ),
            )

    # Try to connect via CDP
    from naturo.cdp import CDPClient, CDPConnectionError as CDPConnErr

    try:
        client = CDPClient(port=port)
        tabs = client.list_tabs()
        return {
            "port": port,
            "tabs": tabs,
            "count": len(tabs),
        }
    except CDPConnErr as exc:
        raise NaturoError(
            code="CDP_CONNECTION_ERROR",
            message=f"Cannot connect to {app_name} on port {port}: {exc}",
        ) from exc
