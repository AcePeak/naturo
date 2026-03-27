"""Windows Service management backend.

Provides list/status/start/stop/restart for Windows services
using ``subprocess`` calls to ``sc.exe`` and ``net`` commands.
All functions return structured dicts for easy JSON serialisation.

Phase 5C.3 — Windows Service Management.
"""

from __future__ import annotations

import platform
import re
import subprocess
from typing import Any

from naturo.errors import NaturoError


def _require_windows() -> None:
    """Raise NaturoError if not running on Windows.

    Raises:
        NaturoError: If the current platform is not Windows.
    """
    if platform.system() != "Windows":
        raise NaturoError(
            code="PLATFORM_ERROR",
            message="Service operations require Windows.",
        )


def _run_sc(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    """Run an sc.exe command and return the result.

    Args:
        *args: Arguments to pass to sc.exe.
        check: Whether to raise on non-zero exit code.

    Returns:
        CompletedProcess with stdout/stderr.
    """
    cmd = ["sc.exe"] + list(args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )


def _parse_sc_query_output(output: str) -> list[dict[str, Any]]:
    """Parse sc.exe query output into a list of service dicts.

    Args:
        output: Raw stdout from ``sc query`` or ``sc queryex``.

    Returns:
        List of service info dicts.
    """
    services: list[dict[str, Any]] = []
    current: dict[str, Any] = {}

    for line in output.splitlines():
        line = line.strip()
        if not line:
            if current:
                services.append(current)
                current = {}
            continue

        if line.startswith("SERVICE_NAME:"):
            if current:
                services.append(current)
            current = {"name": line.split(":", 1)[1].strip()}
        elif line.startswith("DISPLAY_NAME:"):
            current["display_name"] = line.split(":", 1)[1].strip()
        elif line.startswith("TYPE"):
            val = line.split(":", 1)[1].strip()
            current["type"] = val
        elif line.startswith("STATE"):
            val = line.split(":", 1)[1].strip()
            # e.g. "4  RUNNING" → extract state name
            match = re.search(r"\b(STOPPED|RUNNING|PAUSED|START_PENDING|STOP_PENDING|CONTINUE_PENDING|PAUSE_PENDING)\b", val)
            if match:
                current["state"] = match.group(1).lower()
            else:
                current["state"] = val.lower()
        elif line.startswith("PID"):
            val = line.split(":", 1)[1].strip()
            try:
                current["pid"] = int(val)
            except ValueError:
                current["pid"] = 0

    if current:
        services.append(current)

    return services


def _parse_sc_qc_output(output: str) -> dict[str, Any]:
    """Parse sc.exe qc (query config) output into a dict.

    Args:
        output: Raw stdout from ``sc qc <name>``.

    Returns:
        Service configuration dict.
    """
    config: dict[str, Any] = {}
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("[SC]"):
            continue

        # sc qc uses "KEY_LABEL   : value" format with variable spacing
        # Normalise by collapsing whitespace around the first colon
        if ":" not in line:
            continue
        key_part, _, val_part = line.partition(":")
        key = key_part.strip().upper().replace(" ", "_")
        val = val_part.strip()

        if key == "SERVICE_NAME":
            config["name"] = val
        elif key == "DISPLAY_NAME":
            config["display_name"] = val
        elif key == "TYPE":
            config["type"] = val
        elif key == "START_TYPE":
            match = re.search(
                r"\b(AUTO_START|DEMAND_START|DISABLED|BOOT_START|SYSTEM_START)\b",
                val,
            )
            config["start_type"] = match.group(1).lower() if match else val.lower()
        elif key == "BINARY_PATH_NAME":
            config["binary_path"] = val
        elif key == "DEPENDENCIES":
            config["dependencies"] = [d.strip() for d in val.split("/") if d.strip()] if val else []
        elif key == "SERVICE_START_NAME":
            config["run_as"] = val

    return config


def service_list(
    state: str = "all",
) -> dict[str, Any]:
    """List Windows services.

    Args:
        state: Filter by state — 'running', 'stopped', or 'all'.

    Returns:
        Dict with 'services' list and 'count'.

    Raises:
        NaturoError: If not on Windows or the command fails.
    """
    _require_windows()

    # sc.exe state= only accepts "all" or "inactive".  The default
    # (no state= arg) returns running/active services, which is what
    # "running" means.  Passing "state= active" triggers error 87.
    if state == "running":
        result = _run_sc("queryex", "type=", "service")
    elif state == "stopped":
        result = _run_sc("queryex", "type=", "service", "state=", "inactive")
    else:
        result = _run_sc("queryex", "type=", "service", "state=", "all")
    if result.returncode != 0 and not result.stdout.strip():
        raise NaturoError(
            code="SERVICE_ERROR",
            message=f"Failed to list services: {result.stderr.strip() or 'unknown error'}",
        )

    services = _parse_sc_query_output(result.stdout)
    return {"services": services, "count": len(services)}


def service_status(name: str) -> dict[str, Any]:
    """Get detailed status and config of a Windows service.

    Args:
        name: Service name (short name, not display name).

    Returns:
        Dict with service status and configuration.

    Raises:
        NaturoError: If the service is not found or the command fails.
    """
    _require_windows()

    if not name or not name.strip():
        raise NaturoError(
            code="INVALID_INPUT",
            message="Service name cannot be empty.",
        )

    # Query runtime status
    result = _run_sc("queryex", name.strip())
    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "1060" in (result.stdout + result.stderr):
            raise NaturoError(
                code="SERVICE_NOT_FOUND",
                message=f"Service not found: {name}",
            )
        raise NaturoError(
            code="SERVICE_ERROR",
            message=f"Failed to query service '{name}': {stderr or result.stdout.strip()}",
        )

    services = _parse_sc_query_output(result.stdout)
    if not services:
        raise NaturoError(
            code="SERVICE_NOT_FOUND",
            message=f"Service not found: {name}",
        )
    info = services[0]

    # Query config
    qc_result = _run_sc("qc", name.strip())
    if qc_result.returncode == 0:
        config = _parse_sc_qc_output(qc_result.stdout)
        info.update({k: v for k, v in config.items() if k not in info})

    return info


def service_start(name: str) -> dict[str, Any]:
    """Start a Windows service.

    Args:
        name: Service name.

    Returns:
        Dict with operation result.

    Raises:
        NaturoError: If the service is not found, already running, or start fails.
    """
    _require_windows()

    if not name or not name.strip():
        raise NaturoError(
            code="INVALID_INPUT",
            message="Service name cannot be empty.",
        )

    name = name.strip()

    # Check current state first
    status = service_status(name)
    if status.get("state") == "running":
        raise NaturoError(
            code="SERVICE_ALREADY_RUNNING",
            message=f"Service '{name}' is already running.",
        )

    result = subprocess.run(
        ["net", "start", name],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        error_msg = result.stderr.strip() or result.stdout.strip()
        raise NaturoError(
            code="SERVICE_START_FAILED",
            message=f"Failed to start service '{name}': {error_msg}",
        )

    return {"name": name, "action": "start", "state": "running"}


def service_stop(name: str) -> dict[str, Any]:
    """Stop a Windows service.

    Args:
        name: Service name.

    Returns:
        Dict with operation result.

    Raises:
        NaturoError: If the service is not found, already stopped, or stop fails.
    """
    _require_windows()

    if not name or not name.strip():
        raise NaturoError(
            code="INVALID_INPUT",
            message="Service name cannot be empty.",
        )

    name = name.strip()

    # Check current state first
    status = service_status(name)
    if status.get("state") == "stopped":
        raise NaturoError(
            code="SERVICE_ALREADY_STOPPED",
            message=f"Service '{name}' is already stopped.",
        )

    result = subprocess.run(
        ["net", "stop", name],
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.returncode != 0:
        error_msg = result.stderr.strip() or result.stdout.strip()
        raise NaturoError(
            code="SERVICE_STOP_FAILED",
            message=f"Failed to stop service '{name}': {error_msg}",
        )

    return {"name": name, "action": "stop", "state": "stopped"}


def service_restart(name: str) -> dict[str, Any]:
    """Restart a Windows service (stop then start).

    Args:
        name: Service name.

    Returns:
        Dict with operation result.

    Raises:
        NaturoError: If the service is not found or restart fails.
    """
    _require_windows()

    if not name or not name.strip():
        raise NaturoError(
            code="INVALID_INPUT",
            message="Service name cannot be empty.",
        )

    name = name.strip()

    # Check current state
    status = service_status(name)
    if status.get("state") == "running":
        # Stop first
        stop_result = subprocess.run(
            ["net", "stop", name],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if stop_result.returncode != 0:
            error_msg = stop_result.stderr.strip() or stop_result.stdout.strip()
            raise NaturoError(
                code="SERVICE_STOP_FAILED",
                message=f"Failed to stop service '{name}' during restart: {error_msg}",
            )

    # Start
    start_result = subprocess.run(
        ["net", "start", name],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if start_result.returncode != 0:
        error_msg = start_result.stderr.strip() or start_result.stdout.strip()
        raise NaturoError(
            code="SERVICE_START_FAILED",
            message=f"Failed to start service '{name}' during restart: {error_msg}",
        )

    return {"name": name, "action": "restart", "state": "running"}
