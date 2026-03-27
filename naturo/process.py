"""Process management — launch, quit, relaunch, find applications.

Mirrors Peekaboo's ``app`` command subcommands.  Uses the platform backend
for actual operations and adds higher-level logic (wait-until-ready, relaunch).
"""

from __future__ import annotations

import logging
import os
import platform
import signal
import subprocess
import time
from dataclasses import dataclass

from naturo.errors import AppNotFoundError, TimeoutError

logger = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    """Information about a running process.

    Attributes:
        pid: Process ID.
        name: Process/application name.
        path: Executable path (may be empty if not available).
        is_running: Whether the process is currently running.
        window_count: Number of visible windows owned by this process.
    """

    pid: int
    name: str
    path: str = ""
    is_running: bool = True
    window_count: int = 0


def _list_processes() -> list[ProcessInfo]:
    """List running processes using platform-appropriate methods."""
    system = platform.system()
    processes: list[ProcessInfo] = []

    if system == "Windows":
        try:
            # Use tasklist /FO CSV for simple parsing
            # Force UTF-8 encoding to handle Unicode process names (e.g. Chinese)
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=10,
            )
            for line in result.stdout.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                parts = line.split('","')
                if len(parts) >= 2:
                    name = parts[0].strip('"')
                    try:
                        pid = int(parts[1].strip('"'))
                    except (ValueError, IndexError):
                        continue
                    processes.append(ProcessInfo(pid=pid, name=name, is_running=True))
        except Exception as exc:
            logger.debug("Failed to list processes on Windows: %s", exc)
    else:
        # Unix-like: use ps
        try:
            result = subprocess.run(
                ["ps", "-eo", "pid,comm"],
                capture_output=True, text=True, timeout=10,
            )
            for line in result.stdout.strip().split("\n")[1:]:  # skip header
                parts = line.strip().split(None, 1)
                if len(parts) >= 2:
                    try:
                        pid = int(parts[0])
                    except ValueError:
                        continue
                    name = parts[1]
                    processes.append(ProcessInfo(pid=pid, name=name, is_running=True))
        except Exception as exc:
            logger.debug("Failed to list processes: %s", exc)

    return processes


def _get_console_session_id() -> int:
    """Get the active console (interactive desktop) session ID on Windows.

    Uses WTSGetActiveConsoleSessionId to determine which Windows session
    owns the physical console.

    Returns:
        Active console session ID, or -1 on failure or non-Windows.
    """
    if platform.system() != "Windows":
        return -1
    try:
        import ctypes
        session_id = ctypes.windll.kernel32.WTSGetActiveConsoleSessionId()
        if session_id == 0xFFFFFFFF:
            return -1
        return session_id
    except Exception:
        return -1


def _get_process_session_id(pid: int) -> int:
    """Get the Windows session ID for a process.

    Args:
        pid: Process ID.

    Returns:
        Session ID, or -1 on failure or non-Windows.
    """
    if platform.system() != "Windows":
        return -1
    try:
        import ctypes
        import ctypes.wintypes
        session_id = ctypes.wintypes.DWORD()
        success = ctypes.windll.kernel32.ProcessIdToSessionId(
            pid, ctypes.byref(session_id)
        )
        if success:
            return session_id.value
        return -1
    except Exception:
        return -1


def find_process(
    name: str | None = None,
    pid: int | None = None,
    *,
    require_interactive: bool = False,
) -> ProcessInfo | None:
    """Find a running process by name or PID.

    When searching by name, prefers processes in the active console session
    over those in Session 0 (non-interactive services session).  This
    prevents schtasks/remote contexts from targeting ghost processes (#230).

    Args:
        name: Process name (case-insensitive substring match).
        pid: Process ID.
        require_interactive: When True, skip session 0 processes entirely
            instead of falling back to them.  Use this for operations that
            need a visible desktop process (e.g. ``app inspect``,
            ``app launch`` readiness checks).  (#350)

    Returns:
        ProcessInfo if found, None otherwise.
    """
    if name is None and pid is None:
        return None

    processes = _list_processes()

    # PID lookup is exact — no session preference needed
    if pid is not None:
        for proc in processes:
            if proc.pid == pid:
                return proc
        return None

    # Name lookup: prefer interactive session processes (#230)
    assert name is not None
    name_lower = name.lower()
    first_match: ProcessInfo | None = None
    console_session = _get_console_session_id()

    for proc in processes:
        if name_lower not in proc.name.lower():
            continue

        # Session-aware filtering (#350): when require_interactive is True
        # and we can determine session IDs, skip session 0 processes entirely.
        if require_interactive and console_session >= 0:
            proc_session = _get_process_session_id(proc.pid)
            if proc_session == 0:
                continue  # Skip non-interactive services session

        if first_match is None:
            first_match = proc
        # If we can determine sessions, prefer the console session
        if console_session >= 0:
            proc_session = _get_process_session_id(proc.pid)
            if proc_session == console_session:
                return proc  # Found an interactive session match — use it

    return first_match  # Fallback to first match if no console session match


def is_running(name: str) -> bool:
    """Check if an application is currently running.

    Args:
        name: Application/process name (case-insensitive substring match).

    Returns:
        True if at least one matching process is found.
    """
    return find_process(name=name) is not None


# Launch aliases: map user-friendly names to executable names for launching.
# These mirror _APP_ALIASES in WindowsBackend but only include entries
# where the alias resolves to an actual executable basename (no CJK display
# names since those aren't valid for ``where`` / ``start``).
_LAUNCH_ALIASES: dict[str, list[str]] = {
    "calculator": ["calc", "calculatorapp"],
    "计算器": ["calc", "calculatorapp"],
    "paint": ["mspaint"],
    "画图": ["mspaint"],
    "settings": ["systemsettings"],
    "设置": ["systemsettings"],
    "notepad": ["notepad"],
    "记事本": ["notepad"],
    "explorer": ["explorer"],
    "file explorer": ["explorer"],
    "文件资源管理器": ["explorer"],
    "edge": ["msedge"],
    "task manager": ["taskmgr"],
    "任务管理器": ["taskmgr"],
    "command prompt": ["cmd"],
    "命令提示符": ["cmd"],
    "terminal": ["windowsterminal"],
    "终端": ["windowsterminal"],
}


def _resolve_launch_name(name: str) -> str:
    """Resolve a user-friendly app name to a launchable executable name.

    Checks if the given *name* is directly resolvable via ``where`` on
    Windows.  If not, looks up ``_LAUNCH_ALIASES`` and returns the first
    alias that ``where`` can find.  Falls back to the original *name*
    when no alias resolves.

    Args:
        name: User-provided application name (e.g. "calculator").

    Returns:
        An executable name that the system can launch (e.g. "calc").
    """
    if platform.system() != "Windows":
        return name

    # If the name itself is directly resolvable, use it as-is.
    try:
        result = subprocess.run(
            ["where", name], capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return name
    except (subprocess.TimeoutExpired, OSError):
        pass

    # Try aliases
    aliases = _LAUNCH_ALIASES.get(name.lower(), [])
    for alias in aliases:
        try:
            result = subprocess.run(
                ["where", alias], capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return alias
        except (subprocess.TimeoutExpired, OSError):
            continue

    # Last resort: return first alias if available (let ``start`` try it),
    # otherwise the original name.
    return aliases[0] if aliases else name


def launch_app(
    name: str | None = None,
    path: str | None = None,
    wait_until_ready: bool = False,
    timeout: float = 30.0,
    args: list[str] | None = None,
    no_focus: bool = False,
) -> ProcessInfo:
    """Launch an application.

    On Windows, verifies that the current session is interactive before
    launching.  SSH sessions spawn processes in session 0 (invisible),
    which creates orphaned processes and misleads callers (#351).

    Args:
        name: Application name (resolved via system mechanisms).
        path: Explicit executable path.
        wait_until_ready: Wait for the app to create a window.
        timeout: Seconds to wait for ready (only if wait_until_ready).
        args: Additional command-line arguments.
        no_focus: Launch without focusing (platform-specific).

    Returns:
        ProcessInfo for the launched application.

    Raises:
        AppNotFoundError: If the application cannot be found or launched.
        NoDesktopSessionError: If running in a non-interactive session on
            Windows (e.g. SSH without desktop).
        TimeoutError: If wait_until_ready times out.
    """
    launch_target = path or name
    if not launch_target:
        raise AppNotFoundError("(no name or path provided)")

    # Guard: prevent launching GUI apps in non-interactive sessions (#351).
    # SSH sessions spawn processes in session 0 (invisible on the desktop),
    # creating orphaned processes that accumulate over time.
    if platform.system() == "Windows":
        from naturo.cli.interaction import _is_current_session_interactive
        if not _is_current_session_interactive():
            from naturo.errors import NoDesktopSessionError
            raise NoDesktopSessionError(
                "Cannot launch GUI applications in a non-interactive session "
                "(SSH/service).  Processes would be spawned in session 0 "
                "(invisible on the desktop).  Connect via RDP or Console instead."
            )

    cmd_args = args or []
    system = platform.system()

    try:
        if system == "Windows":
            if path:
                # Verify path exists before launching
                if not os.path.isfile(path):
                    raise AppNotFoundError(launch_target, suggested_action="File does not exist")
                proc = subprocess.Popen([path] + cmd_args)
            else:
                # Resolve the launch name: try the original name first,
                # then fall back to alias-resolved executable names.
                resolved_name = _resolve_launch_name(name or "")

                # Use 'where' to verify command exists, then 'start'
                try:
                    where_result = subprocess.run(
                        ["where", resolved_name],
                        capture_output=True, text=True, timeout=5,
                    )
                except (subprocess.TimeoutExpired, subprocess.CalledProcessError, OSError):
                    where_result = type("R", (), {"returncode": 1})()
                if where_result.returncode != 0:
                    # Also check if it's a known app via start — run synchronously to check
                    try:
                        result = subprocess.run(
                            ["cmd", "/c", "start", "/wait", "", resolved_name] + cmd_args,
                            capture_output=True, text=True, timeout=10,
                        )
                    except subprocess.TimeoutExpired:
                        # Windows shows an error dialog for unknown apps; timeout is expected
                        raise AppNotFoundError(
                            launch_target,
                            suggested_action="Application not found or failed to launch",
                        )
                    if result.returncode != 0:
                        raise AppNotFoundError(launch_target)
                    # start /wait succeeded but we need to find the PID now
                    found = find_process(name=resolved_name)
                    if not found and resolved_name != (name or ""):
                        found = find_process(name=name)
                    if found:
                        return found
                    # Launched but already exited — report success with a dummy PID
                    return ProcessInfo(pid=0, name=name or "", path="", is_running=False)
                proc = subprocess.Popen(["cmd", "/c", "start", "", resolved_name] + cmd_args)
        elif system == "Darwin":
            if path:
                proc = subprocess.Popen([path] + cmd_args)
            else:
                open_args = ["open", "-a", name or ""]
                if no_focus:
                    open_args.append("-g")
                if cmd_args:
                    open_args.append("--args")
                    open_args.extend(cmd_args)
                proc = subprocess.Popen(open_args)
                # 'open -a' exits quickly; check its return code
                try:
                    retcode = proc.wait(timeout=10)
                    if retcode is not None and retcode != 0:
                        raise AppNotFoundError(launch_target)
                except subprocess.TimeoutExpired:
                    pass  # Still running, treat as success
        else:
            # Linux
            target = path or name or ""
            proc = subprocess.Popen([target] + cmd_args)
            # Check if the process exits immediately with an error
            try:
                retcode = proc.wait(timeout=2)
                if retcode is not None and retcode != 0:
                    raise AppNotFoundError(launch_target)
            except subprocess.TimeoutExpired:
                pass  # Still running, treat as success
    except AppNotFoundError:
        raise
    except subprocess.TimeoutExpired:
        raise AppNotFoundError(
            launch_target,
            suggested_action="Application did not start within the expected time. "
            "Verify the application name is correct and installed.",
        )
    except FileNotFoundError:
        raise AppNotFoundError(launch_target)
    except OSError as exc:
        raise AppNotFoundError(launch_target, suggested_action=str(exc))

    info = ProcessInfo(
        pid=proc.pid,
        name=name or os.path.basename(path or ""),
        path=path or "",
        is_running=True,
        window_count=0,
    )

    if wait_until_ready:
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            time.sleep(0.5)
            # Check if process is still alive
            if proc.poll() is not None:
                raise AppNotFoundError(
                    launch_target,
                    suggested_action="Process exited immediately after launch",
                )
            # On any platform, if the process is running, consider it "ready"
            # A more thorough check would look for windows, but that requires the backend
            info.is_running = True
            return info

        raise TimeoutError(
            f"Timed out waiting for {launch_target} to be ready",
            timeout=timeout,
        )

    return info


def quit_app(
    name: str | None = None,
    pid: int | None = None,
    force: bool = False,
    timeout: float = 10.0,
) -> None:
    """Quit an application gracefully, force-kill on timeout.

    Args:
        name: Application name.
        pid: Process ID.
        force: Skip graceful shutdown, kill immediately.
        timeout: Seconds to wait for graceful shutdown before force-killing.

    Raises:
        AppNotFoundError: If no matching process is found.
    """
    proc = find_process(name=name, pid=pid)
    if proc is None:
        identifier = name or str(pid)
        raise AppNotFoundError(identifier)

    target_pid = proc.pid
    system = platform.system()

    if force:
        _force_kill(target_pid, system)
        return

    # Graceful shutdown
    try:
        if system == "Windows":
            subprocess.run(
                ["taskkill", "/PID", str(target_pid)],
                capture_output=True, timeout=timeout,
            )
        else:
            os.kill(target_pid, signal.SIGTERM)
    except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
        pass

    # Wait for exit
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        if not is_running(name or "") and (name is not None):
            return
        if pid is not None and find_process(pid=pid) is None:
            return
        time.sleep(0.3)

    # Force kill as fallback
    _force_kill(target_pid, system)


def _force_kill(pid: int, system: str) -> None:
    """Force-kill a process by PID."""
    try:
        if system == "Windows":
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, timeout=10,
            )
        else:
            os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, OSError, subprocess.TimeoutExpired):
        pass  # Already dead


def relaunch_app(
    name: str,
    wait_until_ready: bool = True,
    timeout: float = 30.0,
) -> ProcessInfo:
    """Quit and relaunch an application.

    Args:
        name: Application name.
        wait_until_ready: Wait for the relaunched app to be ready.
        timeout: Seconds to wait.

    Returns:
        ProcessInfo for the relaunched application.
    """
    # Try to quit first (ignore if not running)
    try:
        quit_app(name=name, timeout=min(timeout / 3, 10.0))
    except AppNotFoundError:
        pass

    # Brief pause to let resources release
    time.sleep(0.5)

    return launch_app(
        name=name,
        wait_until_ready=wait_until_ready,
        timeout=timeout,
    )


def list_apps() -> list[ProcessInfo]:
    """List running applications (unique by name).

    Returns:
        Deduplicated list of ProcessInfo objects.
    """
    all_procs = _list_processes()

    # Deduplicate by name, keeping the first occurrence
    seen: set[str] = set()
    unique: list[ProcessInfo] = []
    for proc in all_procs:
        key = proc.name.lower()
        if key not in seen:
            seen.add(key)
            unique.append(proc)

    return unique
