"""Naturo error framework — structured errors aligned with Peekaboo's StandardErrorCode.

All Naturo operations raise subclasses of :class:`NaturoError` with machine-readable
error codes, categories, and optional recovery hints.  CLI commands format these as
JSON when ``--json`` is active.
"""

from __future__ import annotations

from typing import Any


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
    STALE_SNAPSHOT_CACHE = "STALE_SNAPSHOT_CACHE"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    RECORDING_NOT_FOUND = "RECORDING_NOT_FOUND"
    SELECTOR_NOT_FOUND = "SELECTOR_NOT_FOUND"
    BASELINE_NOT_FOUND = "BASELINE_NOT_FOUND"

    # Operation errors
    CAPTURE_FAILED = "CAPTURE_FAILED"
    SCREENSHOT_FAILED = "SCREENSHOT_FAILED"
    INTERACTION_FAILED = "INTERACTION_FAILED"
    TIMEOUT = "TIMEOUT"
    CANCELLED = "CANCELLED"

    # Input errors
    INVALID_INPUT = "INVALID_INPUT"
    INVALID_COORDINATES = "INVALID_COORDINATES"

    # Image-matching errors (naturo find/click --image, #1059)
    INVALID_TEMPLATE = "INVALID_TEMPLATE"
    INVALID_SCREENSHOT = "INVALID_SCREENSHOT"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    PLATFORM_ERROR = "PLATFORM_ERROR"

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
    WORKTREE_MISMATCH = "WORKTREE_MISMATCH"
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


# Canonical ``code -> category`` map. Single source of truth for the *raw-code*
# JSON error path (:func:`naturo.cli.error_helpers.json_error`), where only an
# error-code string is available — no :class:`NaturoError` instance to read the
# category from. Keeping it here, beside the codes and the subclasses that define
# them, lets every error converge on one ``category`` regardless of whether it was
# raised as an exception or emitted by code string. Codes absent here fall back to
# :attr:`ErrorCategory.UNKNOWN`. ``tests/test_error_envelope_884.py`` asserts this
# map agrees with every NaturoError subclass that fixes a category.
_ERROR_CATEGORIES: dict[str, str] = {
    ErrorCode.PERMISSION_DENIED: ErrorCategory.PERMISSIONS,
    ErrorCode.APP_NOT_FOUND: ErrorCategory.AUTOMATION,
    ErrorCode.WINDOW_NOT_FOUND: ErrorCategory.AUTOMATION,
    ErrorCode.ELEMENT_NOT_FOUND: ErrorCategory.AUTOMATION,
    ErrorCode.MENU_NOT_FOUND: ErrorCategory.AUTOMATION,
    ErrorCode.SNAPSHOT_NOT_FOUND: ErrorCategory.SESSION,
    ErrorCode.STALE_SNAPSHOT_CACHE: ErrorCategory.SESSION,
    # Named, naturo-managed artifacts the user saves and recalls by name — the
    # same family as snapshots, hence ``session`` (see #1101).
    ErrorCode.SELECTOR_NOT_FOUND: ErrorCategory.SESSION,
    ErrorCode.BASELINE_NOT_FOUND: ErrorCategory.SESSION,
    ErrorCode.RECORDING_NOT_FOUND: ErrorCategory.SESSION,
    ErrorCode.FILE_NOT_FOUND: ErrorCategory.IO,
    ErrorCode.CAPTURE_FAILED: ErrorCategory.AUTOMATION,
    # A browser/CDP screenshot that failed to render or encode is an automation
    # operation failure, alongside CAPTURE_FAILED (#1135).
    ErrorCode.SCREENSHOT_FAILED: ErrorCategory.AUTOMATION,
    ErrorCode.INTERACTION_FAILED: ErrorCategory.AUTOMATION,
    ErrorCode.TIMEOUT: ErrorCategory.AUTOMATION,
    # Cancellation is an operation-lifecycle outcome, like ``TIMEOUT`` (#1101).
    ErrorCode.CANCELLED: ErrorCategory.AUTOMATION,
    # Locating a tray icon / taskbar item is UI-element lookup, like
    # app/window/element-not-found (#1101).
    ErrorCode.TRAY_ICON_NOT_FOUND: ErrorCategory.AUTOMATION,
    ErrorCode.TASKBAR_ITEM_NOT_FOUND: ErrorCategory.AUTOMATION,
    # The Windows registry is a persistent key-value store — registry failures
    # are I/O against it (#1101).
    ErrorCode.REGISTRY_NOT_FOUND: ErrorCategory.IO,
    ErrorCode.REGISTRY_ERROR: ErrorCategory.IO,
    ErrorCode.REGISTRY_HAS_SUBKEYS: ErrorCategory.IO,
    ErrorCode.INVALID_INPUT: ErrorCategory.VALIDATION,
    ErrorCode.INVALID_COORDINATES: ErrorCategory.VALIDATION,
    # Image-matching codes (#1059): a template/screenshot the user supplied that
    # cannot be decoded is a validation fault; a missing optional matcher
    # dependency is configuration; a GUI-less platform is environment.
    ErrorCode.INVALID_TEMPLATE: ErrorCategory.VALIDATION,
    ErrorCode.INVALID_SCREENSHOT: ErrorCategory.VALIDATION,
    ErrorCode.MISSING_DEPENDENCY: ErrorCategory.CONFIGURATION,
    ErrorCode.PLATFORM_ERROR: ErrorCategory.ENVIRONMENT,
    ErrorCode.DIALOG_NOT_FOUND: ErrorCategory.AUTOMATION,
    ErrorCode.DEPENDENCY_MISSING: ErrorCategory.CONFIGURATION,
    ErrorCode.NO_DESKTOP_SESSION: ErrorCategory.ENVIRONMENT,
    ErrorCode.FILE_IO_ERROR: ErrorCategory.IO,
    ErrorCode.WORKTREE_MISMATCH: ErrorCategory.ENVIRONMENT,
    ErrorCode.UNKNOWN_ERROR: ErrorCategory.UNKNOWN,
    ErrorCode.AI_PROVIDER_UNAVAILABLE: ErrorCategory.AI,
    ErrorCode.AI_ANALYSIS_FAILED: ErrorCategory.AI,
}


def category_for_code(code: str) -> str:
    """Return the canonical error category for a raw error code.

    Used by the raw-code JSON error path (:func:`naturo.cli.error_helpers.json_error`)
    so an error emitted by code string alone carries the same ``category`` as the
    equivalent :class:`NaturoError` would. Unrecognised codes degrade gracefully to
    :attr:`ErrorCategory.UNKNOWN` rather than raising.

    Args:
        code: A standardized error-code string (e.g. ``"WINDOW_NOT_FOUND"``).

    Returns:
        The matching :class:`ErrorCategory` string, or ``ErrorCategory.UNKNOWN``.
    """
    return _ERROR_CATEGORIES.get(code, ErrorCategory.UNKNOWN)


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


class StaleSnapshotCacheError(NaturoError):
    """Element ref could not be resolved against the snapshot cache.

    Raised when a ``get``/``set`` (or any ref-targeting command) is given an
    element ref (e.g. ``e47``) that is absent from the most recent snapshot —
    typically because no ``naturo see`` has run yet, or the cached snapshot is
    stale and no longer contains that ref. Carries a semantic ``code`` and a
    ``suggested_action`` so machine consumers can dispatch on the error and
    self-correct instead of parsing the human message (see issue #877).
    """

    def __init__(self, ref: str, **kwargs: Any) -> None:
        kwargs.setdefault(
            "suggested_action",
            "Run 'naturo see' to capture a fresh element snapshot, then retry.",
        )
        kwargs.setdefault("is_recoverable", True)
        super().__init__(
            message=(
                f"Element ref '{ref}' not found in snapshot cache. "
                f"Run 'naturo see' first to capture elements."
            ),
            code=ErrorCode.STALE_SNAPSHOT_CACHE,
            category=ErrorCategory.SESSION,
            context={"ref": ref},
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


class WorktreeMismatchError(NaturoError):
    """Imported ``naturo`` resolves outside the expected worktree root.

    Raised by the opt-in import guard (#971) when a stale editable install
    shadows the checkout under test with a sibling worktree's code, which would
    otherwise let runtime verification silently validate the wrong source.
    """

    def __init__(self, message: str, **kwargs: Any) -> None:
        kwargs.setdefault(
            "suggested_action",
            "The imported 'naturo' is not under NATURO_EXPECTED_ROOT. Re-run "
            "'pip install -e .' from the active worktree (or fix the stale "
            ".pth/egg-link), or unset NATURO_EXPECTED_ROOT if the guard is "
            "misconfigured.",
        )
        super().__init__(
            message=message,
            code=ErrorCode.WORKTREE_MISMATCH,
            category=ErrorCategory.ENVIRONMENT,
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
