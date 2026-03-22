"""Naturo error framework — structured errors aligned with Peekaboo's StandardErrorCode.

All Naturo operations raise subclasses of :class:`NaturoError` with machine-readable
error codes, categories, and optional recovery hints.  CLI commands format these as
JSON when ``--json`` is active.
"""

from __future__ import annotations

from typing import Any, Optional


class ErrorCode:
    """Standardized error codes matching Peekaboo's StandardErrorCode strings."""

    # Permission errors
    PERMISSION_DENIED = "PERMISSION_DENIED"

    # Not found errors
    APP_NOT_FOUND = "APP_NOT_FOUND"
    WINDOW_NOT_FOUND = "WINDOW_NOT_FOUND"
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    MENU_NOT_FOUND = "MENU_NOT_FOUND"
    SNAPSHOT_NOT_FOUND = "SNAPSHOT_NOT_FOUND"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"

    # Operation errors
    CAPTURE_FAILED = "CAPTURE_FAILED"
    INTERACTION_FAILED = "INTERACTION_FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"

    # Input errors
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_COORDINATES = "INVALID_COORDINATES"

    # Dialog errors
    DIALOG_NOT_FOUND = "DIALOG_NOT_FOUND"

    # Taskbar / Tray errors
    TASKBAR_ITEM_NOT_FOUND = "TASKBAR_ITEM_NOT_FOUND"
    TRAY_ICON_NOT_FOUND = "TRAY_ICON_NOT_FOUND"

    # Dependency errors
    DEPENDENCY_MISSING = "DEPENDENCY_MISSING"

    # System / environment errors
    NO_DESKTOP_SESSION = "NO_DESKTOP_SESSION"
    FILE_IO_ERROR = "FILE_IO_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

    # AI errors
    AI_PROVIDER_UNAVAILABLE = "AI_PROVIDER_UNAVAILABLE"
    AI_ANALYSIS_FAILED = "AI_ANALYSIS_FAILED"

    # Registry errors
    REGISTRY_NOT_FOUND = "REGISTRY_NOT_FOUND"
    REGISTRY_ERROR = "REGISTRY_ERROR"
    REGISTRY_HAS_SUBKEYS = "REGISTRY_HAS_SUBKEYS"


class ErrorCategory:
    """Error category strings for grouping related errors."""

    PERMISSIONS = "permissions"
    AUTOMATION = "automation"
    CONFIGURATION = "configuration"
    ENVIRONMENT = "environment"
    AI = "ai"
    IO = "io"
    NETWORK = "network"
    SESSION = "session"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


class NaturoError(Exception):
    """Base error for all Naturo operations.

    Attributes:
        message: Human-readable error message.
        code: Standardized error code (matches Peekaboo's StandardErrorCode).
        category: Error category string.
        context: Additional context key-value pairs.
        suggested_action: Optional recovery hint.
        is_recoverable: Whether retry might help.
    """

    def __init__(
        self,
        message: str,
        code: str = ErrorCode.UNKNOWN_ERROR,
        category: str = ErrorCategory.UNKNOWN,
        context: dict[str, Any] | None = None,
        suggested_action: str | None = None,
        is_recoverable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.context = context or {}
        self.suggested_action = suggested_action
        self.is_recoverable = is_recoverable

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a dict suitable for JSON output."""
        return {
            "code": self.code,
            "message": self.message,
            "category": self.category,
            "context": self.context,
            "suggested_action": self.suggested_action,
            "recoverable": self.is_recoverable,
        }

    def to_json_response(self) -> dict[str, Any]:
        """Wrap in a standard CLI JSON error envelope."""
        return {
            "success": False,
            "error": self.to_dict(),
        }

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"


# ── Specific error subclasses ────────────────────────────────────────────────


class AppNotFoundError(NaturoError):
    """Application not found."""

    def __init__(self, name: str, **kwargs: Any) -> None:
        kwargs.setdefault(
            "suggested_action",
            f"Check the application name. Try 'naturo app list' to see running apps, "
            f"or 'naturo app launch {name}' to start it first.",
        )
        kwargs.setdefault("is_recoverable", True)
        super().__init__(
            message=f"Application not found: {name}",
            code=ErrorCode.APP_NOT_FOUND,
            category=ErrorCategory.AUTOMATION,
            context={"app": name},
            **kwargs,
        )


class WindowNotFoundError(NaturoError):
    """Window not found."""

    def __init__(self, title: str, **kwargs: Any) -> None:
        kwargs.setdefault(
            "suggested_action",
            f"No window matching '{title}'. Try 'naturo list windows' to see available windows, "
            f"or launch the app first with 'naturo app launch'.",
        )
        kwargs.setdefault("is_recoverable", True)
        super().__init__(
            message=f"Window not found: {title}",
            code=ErrorCode.WINDOW_NOT_FOUND,
            category=ErrorCategory.AUTOMATION,
            context={"window_title": title},
            **kwargs,
        )


class ElementNotFoundError(NaturoError):
    """UI element not found."""

    def __init__(self, selector: str, **kwargs: Any) -> None:
        kwargs.setdefault(
            "suggested_action",
            f"Element '{selector}' not found in the UI tree. Try: "
            f"1) 'naturo see' to inspect the current UI tree, "
            f"2) use a different selector (Role:Name format), "
            f"3) 'naturo wait --element \"{selector}\"' to wait for it to appear.",
        )
        kwargs.setdefault("is_recoverable", True)
        super().__init__(
            message=f"Element not found: {selector}",
            code=ErrorCode.ELEMENT_NOT_FOUND,
            category=ErrorCategory.AUTOMATION,
            context={"selector": selector},
            **kwargs,
        )


class MenuNotFoundError(NaturoError):
    """Menu item not found."""

    def __init__(self, path: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Menu item not found: {path}",
            code=ErrorCode.MENU_NOT_FOUND,
            category=ErrorCategory.AUTOMATION,
            context={"menu_path": path},
            **kwargs,
        )


class SnapshotNotFoundError(NaturoError):
    """Snapshot not found."""

    def __init__(self, snapshot_id: str, **kwargs: Any) -> None:
        super().__init__(
            message=f"Snapshot not found: {snapshot_id}",
            code=ErrorCode.SNAPSHOT_NOT_FOUND,
            category=ErrorCategory.SESSION,
            context={"snapshot_id": snapshot_id},
            **kwargs,
        )


class TimeoutError(NaturoError):
    """Operation timed out."""

    def __init__(self, message: str = "Operation timed out", timeout: float | None = None, **kwargs: Any) -> None:
        ctx = kwargs.pop("context", {})
        if timeout is not None:
            ctx["timeout"] = timeout
        kwargs.setdefault(
            "suggested_action",
            "The element or condition did not appear within the timeout. Try: "
            "1) increase --timeout, "
            "2) check if the target window is in the foreground, "
            "3) take a screenshot to verify the current UI state.",
        )
        super().__init__(
            message=message,
            code=ErrorCode.TIMEOUT,
            category=ErrorCategory.AUTOMATION,
            context=ctx,
            is_recoverable=True,
            **kwargs,
        )


class CaptureFailedError(NaturoError):
    """Screenshot/capture failed."""

    def __init__(self, message: str = "Capture failed", **kwargs: Any) -> None:
        kwargs.setdefault(
            "suggested_action",
            "Screenshot capture failed. Ensure the target window exists and is not minimized. "
            "Try 'naturo list windows' to verify.",
        )
        super().__init__(
            message=message,
            code=ErrorCode.CAPTURE_FAILED,
            category=ErrorCategory.AUTOMATION,
            is_recoverable=True,
            **kwargs,
        )


class InteractionFailedError(NaturoError):
    """Click/type/etc. interaction failed."""

    def __init__(self, message: str = "Interaction failed", **kwargs: Any) -> None:
        kwargs.setdefault(
            "suggested_action",
            "The interaction could not be completed. Try: "
            "1) verify the target element still exists with 'naturo see', "
            "2) use coordinate-based interaction instead, "
            "3) ensure the window is focused with 'naturo window focus'.",
        )
        super().__init__(
            message=message,
            code=ErrorCode.INTERACTION_FAILED,
            category=ErrorCategory.AUTOMATION,
            is_recoverable=True,
            **kwargs,
        )


class InvalidInputError(NaturoError):
    """Invalid user input or parameters."""

    def __init__(self, message: str = "Invalid input", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.INVALID_INPUT,
            category=ErrorCategory.VALIDATION,
            **kwargs,
        )


class InvalidCoordinatesError(NaturoError):
    """Invalid screen coordinates."""

    def __init__(self, x: int | None = None, y: int | None = None, **kwargs: Any) -> None:
        ctx = kwargs.pop("context", {})
        if x is not None:
            ctx["x"] = x
        if y is not None:
            ctx["y"] = y
        super().__init__(
            message=f"Invalid coordinates: ({x}, {y})",
            code=ErrorCode.INVALID_COORDINATES,
            category=ErrorCategory.VALIDATION,
            context=ctx,
            **kwargs,
        )


class PermissionDeniedError(NaturoError):
    """Insufficient permissions."""

    def __init__(self, message: str = "Permission denied", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.PERMISSION_DENIED,
            category=ErrorCategory.PERMISSIONS,
            suggested_action="Check accessibility/automation permissions",
            **kwargs,
        )


class FileIOError(NaturoError):
    """File I/O error."""

    def __init__(self, message: str = "File I/O error", path: str | None = None, **kwargs: Any) -> None:
        ctx = kwargs.pop("context", {})
        if path:
            ctx["path"] = path
        super().__init__(
            message=message,
            code=ErrorCode.FILE_IO_ERROR,
            category=ErrorCategory.IO,
            context=ctx,
            is_recoverable=True,
            **kwargs,
        )


class DialogNotFoundError(NaturoError):
    """No dialog detected."""

    def __init__(self, message: str = "No dialog detected", **kwargs: Any) -> None:
        kwargs.setdefault(
            "suggested_action",
            "No active dialog found. The dialog may have already closed, or none was triggered. "
            "Use 'naturo dialog detect' to check, or 'naturo wait --element \"Dialog\"' to wait.",
        )
        kwargs.setdefault("is_recoverable", True)
        super().__init__(
            message=message,
            code=ErrorCode.DIALOG_NOT_FOUND,
            category=ErrorCategory.AUTOMATION,
            **kwargs,
        )


class AIProviderUnavailableError(NaturoError):
    """AI provider is unavailable."""

    def __init__(self, provider: str = "unknown", **kwargs: Any) -> None:
        super().__init__(
            message=f"AI provider unavailable: {provider}",
            code=ErrorCode.AI_PROVIDER_UNAVAILABLE,
            category=ErrorCategory.AI,
            context={"provider": provider},
            is_recoverable=True,
            **kwargs,
        )


class AIAnalysisFailedError(NaturoError):
    """AI analysis/inference failed."""

    def __init__(self, message: str = "AI analysis failed", **kwargs: Any) -> None:
        super().__init__(
            message=message,
            code=ErrorCode.AI_ANALYSIS_FAILED,
            category=ErrorCategory.AI,
            is_recoverable=True,
            **kwargs,
        )


class DependencyMissingError(NaturoError):
    """A required dependency (native library, external tool) is missing."""

    def __init__(self, dependency: str, message: str | None = None, **kwargs: Any) -> None:
        msg = message or f"Required dependency missing: {dependency}"
        kwargs.setdefault("is_recoverable", True)
        super().__init__(
            message=msg,
            code=ErrorCode.DEPENDENCY_MISSING,
            category=ErrorCategory.CONFIGURATION,
            context={"dependency": dependency},
            **kwargs,
        )


class NoDesktopSessionError(NaturoError):
    """Raised when a GUI command runs without an interactive desktop session.

    Typical scenario: running naturo commands over SSH or as a Windows service
    where no desktop (explorer shell) is available.
    """

    def __init__(
        self,
        message: str | None = None,
        *,
        command: str | None = None,
        **kwargs: Any,
    ) -> None:
        msg = message or (
            "No interactive desktop session detected. "
            "Naturo GUI commands require a logged-in Windows desktop with an active session. "
            "If connecting via SSH, use RDP or a VNC session instead."
        )
        super().__init__(
            message=msg,
            code=ErrorCode.NO_DESKTOP_SESSION,
            category=ErrorCategory.ENVIRONMENT,
            suggested_action=(
                "Connect via RDP or VNC to get a desktop session, "
                "or run naturo on the machine's physical console."
            ),
            is_recoverable=False,
            context={"command": command} if command else {},
            **kwargs,
        )
