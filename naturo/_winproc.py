"""Resilient Windows process-info queries.

``wmic`` is deprecated and is absent by default on Windows 11 24H2 and later
(it is now an on-demand feature Microsoft is removing), so any code path that
shells out to it silently returns nothing there — breaking Electron detection,
CDP port discovery, and backend routing. Every lookup here tries ``wmic`` first
(fast, and the path our existing tests exercise) and transparently falls back to
a PowerShell ``Get-CimInstance Win32_Process`` call when ``wmic`` is missing or
cannot run. Both paths return the same shapes, so callers stay agnostic.

The CIM fallback speaks JSON, which is delimiter-safe: a command line containing
commas or quotes round-trips correctly, unlike the ``wmic`` CSV format.
"""
from __future__ import annotations

import json
import logging
import subprocess
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

#: Per-PID lookups are cheap; give them a short leash.
_WMIC_PID_TIMEOUT = 5
#: Whole-machine enumerations pay for every process; allow more headroom.
_WMIC_BULK_TIMEOUT = 15
#: PowerShell start-up + CIM is slower than wmic; the fallback gets extra time.
_CIM_TIMEOUT = 20


# ── Subprocess runners ──────────────────────────────────────────────────────


def _run_wmic(args: List[str], timeout: int) -> Optional[str]:
    """Run ``wmic <args>`` and return its stdout, or ``None`` if wmic can't run.

    A returned string (even empty) means wmic executed — callers treat that as
    authoritative and do NOT fall back. ``None`` means wmic is unavailable
    (removed / not on PATH) or timed out, which is the signal to try CIM.
    """
    try:
        result = subprocess.run(
            ["wmic", *args],
            capture_output=True, text=True, errors="replace", timeout=timeout,
        )
        return result.stdout or ""
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("wmic unavailable (%s); will try CIM fallback", exc)
        return None


def _cim_query(where: str = "") -> List[dict]:
    """Return ``Win32_Process`` rows as dicts via PowerShell CIM.

    ``where`` is an optional WQL filter (e.g. ``"ProcessId=1234"``). Returns an
    empty list on any failure. A single-row result comes back from
    ``ConvertTo-Json`` as one object rather than an array — both are normalized
    to a list here.
    """
    filt = f"-Filter '{where}' " if where else ""
    script = (
        f"Get-CimInstance Win32_Process {filt}| "
        "Select-Object ProcessId,ParentProcessId,CommandLine,ExecutablePath | "
        "ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, errors="replace", timeout=_CIM_TIMEOUT,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("CIM fallback could not run: %s", exc)
        return []
    return _parse_cim_json(result.stdout or "")


# ── Pure parsers (unit-tested) ──────────────────────────────────────────────


def _parse_list_field(stdout: str, field: str) -> Optional[str]:
    """Pull ``field`` from ``wmic ... /format:list`` output (``Field=value``)."""
    prefix = field + "="
    for line in stdout.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):]
    return None


def _parse_bulk_csv(stdout: str) -> Dict[int, Dict[str, str]]:
    """Parse ``wmic process get ProcessId,CommandLine,ExecutablePath /format:csv``.

    Locates the header row (column order varies), then maps each PID to its
    command line and exe path. Ported verbatim from the original electron reader
    so the wmic path stays byte-for-byte compatible.
    """
    info: Dict[int, Dict[str, str]] = {}
    lines = stdout.strip().splitlines()
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
    for line in lines[header_idx + 1:]:
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
    return info


def _parse_parent_csv(stdout: str) -> Dict[int, int]:
    """Parse ``wmic process get ProcessId,ParentProcessId /format:csv`` → {pid: ppid}.

    wmic csv columns are alphabetical: ``Node,ParentProcessId,ProcessId`` — the
    last two fields are ppid then pid.
    """
    parents: Dict[int, int] = {}
    for line in stdout.splitlines():
        parts = line.strip().split(",")
        if len(parts) < 3:
            continue
        try:
            ppid = int(parts[-2])
            cpid = int(parts[-1])
        except ValueError:
            continue
        parents[cpid] = ppid
    return parents


def _parse_cim_json(stdout: str) -> List[dict]:
    """Normalize ``ConvertTo-Json`` output to a list of row dicts (object or array)."""
    text = stdout.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return []
    if isinstance(data, dict):  # single match → one object, not an array
        return [data]
    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]
    return []


# ── Public API (wmic primary, CIM fallback) ─────────────────────────────────


def command_line(pid: int) -> Optional[str]:
    """Full command line of ``pid``, or ``None`` if inaccessible."""
    out = _run_wmic(
        ["process", "where", f"ProcessId={pid}", "get", "CommandLine", "/format:list"],
        _WMIC_PID_TIMEOUT)
    if out is not None:
        return _parse_list_field(out, "CommandLine")
    for row in _cim_query(f"ProcessId={pid}"):
        cl = row.get("CommandLine")
        return cl or None
    return None


def exe_path(pid: int) -> Optional[str]:
    """Executable path of ``pid``, or ``None`` if inaccessible."""
    out = _run_wmic(
        ["process", "where", f"ProcessId={pid}", "get", "ExecutablePath", "/format:list"],
        _WMIC_PID_TIMEOUT)
    if out is not None:
        return _parse_list_field(out, "ExecutablePath")
    for row in _cim_query(f"ProcessId={pid}"):
        ep = row.get("ExecutablePath")
        return ep or None
    return None


def bulk_process_info() -> Dict[int, Dict[str, str]]:
    """Command line + exe path for every process, keyed by PID.

    One call instead of per-PID lookups (the per-PID overhead is what used to
    hang ``electron list`` — BUG-007). Values are ``{command_line, exe_path}``.
    """
    out = _run_wmic(
        ["process", "get", "ProcessId,CommandLine,ExecutablePath", "/format:csv"],
        _WMIC_BULK_TIMEOUT)
    if out is not None:
        return _parse_bulk_csv(out)
    info: Dict[int, Dict[str, str]] = {}
    for row in _cim_query():
        pid = row.get("ProcessId")
        if not isinstance(pid, int):
            continue
        info[pid] = {
            "command_line": row.get("CommandLine") or "",
            "exe_path": row.get("ExecutablePath") or "",
        }
    return info


def parent_map() -> Dict[int, int]:
    """Map every PID to its parent PID (for process-tree descent)."""
    out = _run_wmic(
        ["process", "get", "ProcessId,ParentProcessId", "/format:csv"],
        _WMIC_BULK_TIMEOUT)
    if out is not None:
        return _parse_parent_csv(out)
    parents: Dict[int, int] = {}
    for row in _cim_query():
        pid, ppid = row.get("ProcessId"), row.get("ParentProcessId")
        if isinstance(pid, int) and isinstance(ppid, int):
            parents[pid] = ppid
    return parents
