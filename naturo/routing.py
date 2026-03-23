"""Auto-routing for action commands.

Resolves the best interaction method for a target application by combining
process resolution with the detection chain. Used by click, type, press,
and find commands when ``--method auto`` (the default).

The routing flow:
1. Resolve ``--app`` / ``--pid`` to a process PID
2. Run the detection chain (cached per PID)
3. Return the recommended ``InteractionMethodType``
4. Log the routing decision for transparency

When ``--method`` is set explicitly (not "auto"), routing is bypassed and
the specified method is used directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RoutingResult:
    """Result of auto-routing for a target application.

    Attributes:
        pid: Resolved process ID (None if no app specified).
        app_name: Resolved application name.
        method: Recommended interaction method name (e.g. "uia", "cdp").
        source: How the method was determined — "auto" or "explicit".
        framework: Detected framework type (e.g. "electron", "win32").
        confidence: Detection confidence (0.0–1.0).
    """

    pid: Optional[int] = None
    app_name: str = ""
    method: str = "vision"
    source: str = "auto"
    framework: str = "unknown"
    confidence: float = 0.0

    def to_dict(self) -> dict:
        """Serialize for JSON output."""
        return {
            "pid": self.pid,
            "app": self.app_name,
            "method": self.method,
            "source": self.source,
            "framework": self.framework,
            "confidence": self.confidence,
        }


def resolve_method(
    app: Optional[str] = None,
    pid: Optional[int] = None,
    explicit_method: str = "auto",
) -> RoutingResult:
    """Resolve the best interaction method for a target application.

    When ``explicit_method`` is anything other than "auto", returns that
    method directly without running detection. Otherwise, resolves the
    app/pid to a process and runs the detection chain.

    Args:
        app: Application name (fuzzy matched against running processes).
        pid: Process ID (takes precedence over app name).
        explicit_method: Value from ``--method`` flag. "auto" triggers
            detection; any other value bypasses it.

    Returns:
        RoutingResult with the resolved method and metadata.
    """
    # Explicit override — skip detection entirely
    if explicit_method != "auto":
        logger.info("Method override: %s (skipping auto-detection)", explicit_method)
        return RoutingResult(
            pid=pid,
            app_name=app or "",
            method=explicit_method,
            source="explicit",
        )

    # No target app specified — fall back to vision (coordinate-based)
    if app is None and pid is None:
        logger.debug("No app/pid specified, defaulting to vision method")
        return RoutingResult(method="vision", source="auto")

    # Resolve process
    resolved_pid = pid
    resolved_name = app or ""
    if resolved_pid is None and app is not None:
        try:
            from naturo.process import find_process

            proc = find_process(name=app)
            if proc is not None:
                resolved_pid = proc.pid
                resolved_name = proc.name
                logger.debug("Resolved app %r → PID %d (%s)", app, proc.pid, proc.name)
            else:
                logger.warning("App %r not found among running processes", app)
                return RoutingResult(
                    app_name=app,
                    method="vision",
                    source="auto",
                )
        except Exception as exc:
            logger.debug("Process resolution failed: %s", exc)
            return RoutingResult(
                app_name=app or "",
                method="vision",
                source="auto",
            )

    # Run detection chain
    if resolved_pid is not None:
        try:
            from naturo.detect.chain import detect

            result = detect(pid=resolved_pid, app_name=resolved_name)
            best = result.best_method()
            if best is not None:
                framework_name = (
                    result.frameworks[0].framework_type.value
                    if result.frameworks
                    else "unknown"
                )
                logger.info(
                    "Auto-routing: %s (PID %d) → %s [%s, confidence=%.2f]",
                    resolved_name,
                    resolved_pid,
                    best.method.value,
                    framework_name,
                    best.confidence,
                )
                return RoutingResult(
                    pid=resolved_pid,
                    app_name=resolved_name,
                    method=best.method.value,
                    source="auto",
                    framework=framework_name,
                    confidence=best.confidence,
                )
            else:
                logger.info(
                    "Auto-routing: %s (PID %d) → no methods detected, "
                    "falling back to vision",
                    resolved_name,
                    resolved_pid,
                )
        except Exception as exc:
            logger.debug("Detection chain failed for PID %d: %s", resolved_pid, exc)

    return RoutingResult(
        pid=resolved_pid,
        app_name=resolved_name,
        method="vision",
        source="auto",
    )
