"""Naturo — Windows desktop automation engine."""
from naturo.version import __version__

# Phase 3: Stabilize exports
from naturo.errors import (
    NaturoError, ErrorCode, ErrorCategory,
    AppNotFoundError, WindowNotFoundError, ElementNotFoundError,
    MenuNotFoundError, SnapshotNotFoundError, TimeoutError,
    CaptureFailedError, InteractionFailedError, InvalidInputError,
    InvalidCoordinatesError, PermissionDeniedError, FileIOError,
    AIProviderUnavailableError, AIAnalysisFailedError,
)
from naturo.retry import RetryPolicy, RetryResult, execute_with_retry, with_retry
from naturo.wait import WaitResult, wait_for_element, wait_until_gone, wait_for_window
from naturo.process import ProcessInfo, launch_app, quit_app, relaunch_app, find_process, is_running, list_apps
from naturo.cache import ElementCache
from naturo.diff import ElementChange, TreeDiff, diff_trees

__all__ = [
    "__version__",
    # Errors
    "NaturoError", "ErrorCode", "ErrorCategory",
    "AppNotFoundError", "WindowNotFoundError", "ElementNotFoundError",
    "MenuNotFoundError", "SnapshotNotFoundError", "TimeoutError",
    "CaptureFailedError", "InteractionFailedError", "InvalidInputError",
    "InvalidCoordinatesError", "PermissionDeniedError", "FileIOError",
    "AIProviderUnavailableError", "AIAnalysisFailedError",
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
]
