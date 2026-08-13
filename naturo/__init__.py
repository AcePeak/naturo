"""Naturo — Windows desktop automation engine."""
from naturo.version import __version__

# Phase 3: Stabilize exports
from naturo.errors import (
    NaturoError, ErrorCode, ErrorCategory,
    AppNotFoundError, WindowNotFoundError, ElementNotFoundError,
    MenuNotFoundError, SnapshotNotFoundError, TimeoutError,
    CaptureFailedError, InteractionFailedError, InvalidInputError,
    InvalidCoordinatesError, PermissionDeniedError, FileIOError,
    WorktreeMismatchError,
    AIProviderUnavailableError, AIAnalysisFailedError,
)
from naturo._worktree_guard import check_worktree_integrity
from naturo.retry import RetryPolicy, RetryResult, execute_with_retry, with_retry
from naturo.wait import WaitResult, wait_for_element, wait_until_gone, wait_for_window
from naturo.process import ProcessInfo, launch_app, quit_app, relaunch_app, find_process, is_running, list_apps
from naturo.cache import ElementCache
from naturo.diff import ElementChange, TreeDiff, diff_trees

# Ergonomic in-process Python SDK (#924) — `import naturo` and automate without
# subprocess. Thin wrappers that delegate to the same backend/actions/cascade
# the CLI and MCP surfaces use. Imported last so the base exports above are in
# place before the SDK module (which pulls in backend/actions/mcp helpers).
from naturo import sdk as sdk
# NOTE: `wait` is intentionally NOT re-exported at the top level — it would
# shadow the existing `naturo.wait` submodule (public API, monkeypatched by
# tests). Use ``naturo.Desktop().wait(...)`` (or ``naturo.sdk.wait``) instead.
from naturo.sdk import (
    Desktop, Session, App, Element,
    see, find, click, type, press,
    get_value, set_value, capture,
    launch, quit, windows,
)

# Fail loudly (opt-in via NATURO_EXPECTED_ROOT) if a stale editable install
# resolved this import to a sibling worktree instead of the checkout under test
# (#971). No-op for ordinary installs where the env var is unset.
check_worktree_integrity()

__all__ = [
    "__version__",
    # Errors
    "NaturoError", "ErrorCode", "ErrorCategory",
    "AppNotFoundError", "WindowNotFoundError", "ElementNotFoundError",
    "MenuNotFoundError", "SnapshotNotFoundError", "TimeoutError",
    "CaptureFailedError", "InteractionFailedError", "InvalidInputError",
    "InvalidCoordinatesError", "PermissionDeniedError", "FileIOError",
    "WorktreeMismatchError",
    "AIProviderUnavailableError", "AIAnalysisFailedError",
    # Worktree integrity guard (#971)
    "check_worktree_integrity",
    # Retry
    "RetryPolicy", "RetryResult", "execute_with_retry", "with_retry",
    # Wait
    "WaitResult", "wait_for_element", "wait_until_gone", "wait_for_window",
    # Process
    "ProcessInfo", "launch_app", "quit_app", "relaunch_app", "find_process", "is_running", "list_apps",
    # Cache
    "ElementCache",
    # Diff
    "ElementChange", "TreeDiff", "diff_trees",
    # Python SDK (#924) — `wait` stays a submodule; use Desktop().wait()
    "sdk",
    "Desktop", "Session", "App", "Element",
    "see", "find", "click", "type", "press",
    "get_value", "set_value", "capture",
    "launch", "quit", "windows",
]
