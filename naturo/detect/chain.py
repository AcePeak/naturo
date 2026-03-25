"""Detection chain orchestrator.

Runs framework detection probes in priority order for a target process,
assembles a complete DetectionResult with recommended interaction method.
"""

import logging
import platform
from typing import Callable, List, Optional

from naturo.detect.cache import get_cache
from naturo.detect.models import (
    DetectionResult,
    InteractionMethod,
    InteractionMethodType,
    ProbeStatus,
)
from naturo.detect.probes import (
    detect_frameworks_from_dlls,
    probe_cdp,
    probe_ia2,
    probe_jab,
    probe_msaa,
    probe_uia,
    probe_vision,
)

logger = logging.getLogger(__name__)

# Type alias for probe functions
ProbeFunc = Callable[[int, str, Optional[int]], Optional[InteractionMethod]]

# Default probe chain: ordered from fastest/cheapest to slowest
_DEFAULT_PROBES: List[ProbeFunc] = [
    probe_cdp,
    probe_uia,
    probe_msaa,
    probe_jab,
    probe_ia2,
    probe_vision,
]

# Per-probe timeout in seconds.  CDP and UIA probes can hang on certain
# applications (e.g. UWP Notepad without --quick), so each probe is
# executed with a hard timeout to guarantee the chain always completes.
_PROBE_TIMEOUT_SECONDS = 10


def _run_probe_with_timeout(
    probe_fn: ProbeFunc,
    pid: int,
    exe: str,
    hwnd: Optional[int],
) -> Optional["InteractionMethod"]:
    """Execute a single probe function with a timeout guard.

    Runs the probe in a daemon thread so that a hung probe (e.g. CDP wmic
    call, UIA COM deadlock) cannot block the detection chain forever.
    The thread is abandoned (not joined) on timeout — daemon threads are
    reaped automatically when the process exits.

    Args:
        probe_fn: Probe function to execute.
        pid: Process ID.
        exe: Executable path.
        hwnd: Window handle.

    Returns:
        InteractionMethod from the probe, or None on timeout / error.
    """
    import threading

    result_holder: list = []
    error_holder: list = []

    def _target() -> None:
        try:
            r = probe_fn(pid, exe, hwnd)
            result_holder.append(r)
        except Exception as exc:
            error_holder.append(exc)

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join(timeout=_PROBE_TIMEOUT_SECONDS)

    if t.is_alive():
        logger.warning(
            "Probe %s timed out after %ds for PID %d",
            probe_fn.__name__,
            _PROBE_TIMEOUT_SECONDS,
            pid,
        )
        return None

    if error_holder:
        raise error_holder[0]

    return result_holder[0] if result_holder else None


def detect(
    pid: int,
    exe: str = "",
    hwnd: Optional[int] = None,
    app_name: str = "",
    use_cache: bool = True,
    quick: bool = False,
) -> DetectionResult:
    """Run the full detection chain for a target process.

    Probes are executed in priority order. Each probe returns an
    InteractionMethod or None. Results are assembled into a DetectionResult
    with a recommended (best) interaction method.

    Args:
        pid: Process ID of the target application.
        exe: Executable path (used for heuristic detection).
        hwnd: Window handle (speeds up UIA/MSAA probes if known).
        app_name: Application display name for the result.
        use_cache: Whether to check/populate the per-PID cache.
        quick: If True, stop after the first available method is found
            (skip remaining probes). Faster but less complete.

    Returns:
        DetectionResult with all detected frameworks and methods.
    """
    cache = get_cache()

    # Check cache first
    if use_cache:
        cached = cache.get(pid)
        if cached is not None:
            logger.debug("Cache hit for PID %d", pid)
            return cached

    logger.debug("Running detection chain for PID %d (exe=%s, hwnd=%s)", pid, exe, hwnd)

    # Phase 1: Detect frameworks from DLL signatures
    frameworks = detect_frameworks_from_dlls(pid, exe)

    # Phase 2: Run probes to discover available interaction methods.
    # Each probe runs with a timeout to prevent indefinite hangs (#288).
    methods: List[InteractionMethod] = []
    for probe_fn in _DEFAULT_PROBES:
        try:
            result = _run_probe_with_timeout(probe_fn, pid, exe, hwnd)
            if result is not None:
                methods.append(result)
                # In quick mode, stop at first available method
                if quick and result.status == ProbeStatus.AVAILABLE:
                    logger.debug("Quick mode: stopping after %s", result.method.value)
                    # Still add vision fallback
                    if result.method != InteractionMethodType.VISION:
                        vision = probe_vision(pid, exe, hwnd)
                        methods.append(vision)
                    break
        except Exception as exc:
            logger.warning("Probe %s failed for PID %d: %s", probe_fn.__name__, pid, exc)

    # Sort methods by priority (lower = better)
    methods.sort(key=lambda m: m.priority)

    # Build result
    detection = DetectionResult(
        pid=pid,
        exe=exe,
        app_name=app_name,
        frameworks=frameworks,
        methods=methods,
    )

    # Set recommended method
    best = detection.best_method()
    if best:
        detection.recommended = best.method

    # Populate cache
    if use_cache:
        cache.put(pid, detection)

    logger.debug(
        "Detection complete for PID %d: %d frameworks, %d methods, recommended=%s",
        pid, len(frameworks), len(methods),
        detection.recommended.value if detection.recommended else "none",
    )

    return detection


def detect_for_hwnd(hwnd: int, use_cache: bool = True, quick: bool = False) -> DetectionResult:
    """Run detection chain starting from a window handle.

    Resolves the PID from the window handle, then runs the full chain.

    Args:
        hwnd: Window handle.
        use_cache: Whether to check/populate the per-PID cache.
        quick: If True, stop after first available method.

    Returns:
        DetectionResult for the owning process.

    Raises:
        RuntimeError: If the PID cannot be resolved from the window handle.
    """
    if platform.system() != "Windows":
        raise RuntimeError("detect_for_hwnd requires Windows")

    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    window_pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))

    pid = window_pid.value
    if not pid:
        raise RuntimeError(f"Could not resolve PID for HWND {hwnd}")

    return detect(pid=pid, hwnd=hwnd, use_cache=use_cache, quick=quick)
