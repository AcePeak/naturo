# Naturo Phase 3 — Stabilize (Detailed Spec)

**Goal**: Make naturo reliable for real-world automation. Align error handling, retry, wait, and process management with Peekaboo's interfaces.

## 3.1 Error Handling Framework

### Error Enum: `NaturoError`
File: `naturo/errors.py`

Mirrors Peekaboo's `PeekabooError` enum. Each error has:
- `code: str` — Standardized error code (matches Peekaboo's `StandardErrorCode`)
- `category: str` — Error category
- `message: str` — Human-readable message
- `context: dict` — Additional context key-value pairs
- `suggested_action: str | None` — Recovery hint
- `is_recoverable: bool` — Whether retry might help

```python
class NaturoError(Exception):
    """Base error for all Naturo operations."""
    def __init__(self, message: str, code: str = "UNKNOWN_ERROR",
                 category: str = "unknown", context: dict | None = None,
                 suggested_action: str | None = None, is_recoverable: bool = False):
        ...

# Error codes (match Peekaboo StandardErrorCode)
class ErrorCode:
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
    # System errors
    FILE_IO_ERROR = "FILE_IO_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    # AI errors
    AI_PROVIDER_UNAVAILABLE = "AI_PROVIDER_UNAVAILABLE"
    AI_ANALYSIS_FAILED = "AI_ANALYSIS_FAILED"

class ErrorCategory:
    PERMISSIONS = "permissions"
    AUTOMATION = "automation"
    CONFIGURATION = "configuration"
    AI = "ai"
    IO = "io"
    NETWORK = "network"
    SESSION = "session"
    VALIDATION = "validation"
    UNKNOWN = "unknown"

# Specific error subclasses (mirrors Peekaboo PeekabooError enum cases)
class AppNotFoundError(NaturoError): ...
class WindowNotFoundError(NaturoError): ...
class ElementNotFoundError(NaturoError): ...
class MenuNotFoundError(NaturoError): ...
class SnapshotNotFoundError(NaturoError): ...
class TimeoutError(NaturoError): ...
class CaptureFailedError(NaturoError): ...
class InteractionFailedError(NaturoError): ...
class InvalidInputError(NaturoError): ...
class InvalidCoordinatesError(NaturoError): ...
class PermissionDeniedError(NaturoError): ...
class FileIOError(NaturoError): ...
```

### JSON Error Output
When CLI uses `--json`, errors output as:
```json
{
  "success": false,
  "error": {
    "code": "ELEMENT_NOT_FOUND",
    "message": "Element not found: Button 'Save'",
    "category": "automation",
    "context": {"element": "Button 'Save'"},
    "suggested_action": null,
    "recoverable": false
  }
}
```

### Integration
- All existing backends methods should raise specific `NaturoError` subclasses instead of generic exceptions
- CLI should catch `NaturoError` and format output (text or JSON)
- Existing `bridge.py` error codes should map to `NaturoError`

## 3.2 Wait/Retry Strategies

### RetryPolicy (mirrors Peekaboo RetryPolicy)
File: `naturo/retry.py`

```python
@dataclass
class RetryPolicy:
    max_attempts: int = 3
    initial_delay: float = 0.1  # seconds
    delay_multiplier: float = 2.0
    max_delay: float = 5.0
    retryable_codes: set[str] = field(default_factory=lambda: {
        ErrorCode.TIMEOUT,
        ErrorCode.CAPTURE_FAILED,
        ErrorCode.INTERACTION_FAILED,
        ErrorCode.FILE_IO_ERROR,
        ErrorCode.AI_PROVIDER_UNAVAILABLE,
    })

    # Presets matching Peekaboo
    STANDARD = ...    # default
    AGGRESSIVE = ...  # max_attempts=5, initial_delay=0.05
    CONSERVATIVE = ... # max_attempts=2, initial_delay=0.5
    NO_RETRY = ...    # max_attempts=1

def with_retry(policy: RetryPolicy = RetryPolicy.STANDARD):
    """Decorator and context manager for retry logic."""
    ...
```

### Wait Functions (mirrors Peekaboo waitForElement)
File: `naturo/wait.py`

```python
@dataclass
class WaitResult:
    found: bool
    element: ElementInfo | None
    wait_time: float  # seconds
    warnings: list[str]

def wait_for_element(
    selector: str,
    timeout: float = 10.0,
    poll_interval: float = 0.1,  # 100ms like Peekaboo
    window_title: str | None = None,
) -> WaitResult:
    """Poll for element until found or timeout."""
    ...

def wait_until_gone(
    selector: str,
    timeout: float = 10.0,
    poll_interval: float = 0.1,
    window_title: str | None = None,
) -> WaitResult:
    """Wait until element disappears."""
    ...

def wait_for_window(
    title: str,
    timeout: float = 10.0,
    poll_interval: float = 0.5,
) -> WindowInfo:
    """Wait for window to appear."""
    ...
```

### CLI Integration
```bash
# New --timeout flag on interaction commands
naturo click "Save" --timeout 10
naturo type "hello" --field "Name" --timeout 5

# New wait command
naturo wait --element "Button:Save" --timeout 10
naturo wait --window "Notepad" --timeout 5
naturo wait --gone "Dialog:Loading" --timeout 30
```

## 3.3 Process Management

### Process Functions (mirrors Peekaboo app command)
File: `naturo/process.py`

```python
@dataclass
class ProcessInfo:
    pid: int
    name: str
    path: str
    is_running: bool
    window_count: int

def launch_app(
    name: str | None = None,
    path: str | None = None,
    wait_until_ready: bool = False,  # matches Peekaboo --wait-until-ready
    timeout: float = 30.0,
    args: list[str] | None = None,
    no_focus: bool = False,  # matches Peekaboo --no-focus
) -> ProcessInfo:
    """Launch application, optionally wait for window to appear."""
    ...

def quit_app(
    name: str | None = None,
    pid: int | None = None,
    force: bool = False,
    timeout: float = 10.0,
) -> None:
    """Quit application gracefully, force kill on timeout."""
    ...

def relaunch_app(
    name: str,
    wait_until_ready: bool = True,
    timeout: float = 30.0,
) -> ProcessInfo:
    """Quit then relaunch. Matches Peekaboo app relaunch."""
    ...

def find_process(
    name: str | None = None,
    pid: int | None = None,
) -> ProcessInfo | None:
    """Find running process by name or PID."""
    ...

def is_running(name: str) -> bool:
    """Check if app is running."""
    ...
```

### CLI (mirrors Peekaboo `app` subcommands)
```bash
naturo app launch "Notepad" --wait-until-ready
naturo app launch "calc.exe" --no-focus
naturo app quit --name "Notepad"
naturo app quit --pid 1234 --force
naturo app relaunch "Notepad" --wait-until-ready
naturo app list
naturo app find "Notepad"
```

### Backend Extension
Add to `Backend` abstract class:
```python
# Already have: launch_app, quit_app, list_apps
# Add:
def is_app_running(self, name: str) -> bool: ...
def get_process_info(self, name: str = None, pid: int = None) -> ProcessInfo: ...
def wait_for_app_ready(self, name: str, timeout: float = 30.0) -> bool: ...
```

## 3.4 Performance Optimization

### UIA Caching
File: `naturo/cache.py`

```python
class ElementCache:
    """Cache for UI element trees to reduce COM calls on Windows."""
    def __init__(self, ttl: float = 2.0):  # 2 second TTL
        ...

    def get_tree(self, window_title: str, depth: int) -> ElementInfo | None: ...
    def set_tree(self, window_title: str, depth: int, tree: ElementInfo) -> None: ...
    def invalidate(self, window_title: str | None = None) -> None: ...
    def is_stale(self, window_title: str) -> bool: ...
```

- Backend methods should use cache by default, with `force_refresh=False` parameter
- Cache invalidated automatically after any interaction (click, type, etc.)
- `naturo see --no-cache` to bypass

## 3.5 UI Tree Diff

### Diff Functions
File: `naturo/diff.py`

```python
@dataclass
class ElementChange:
    type: str  # "added", "removed", "modified"
    element_id: str
    element_role: str
    element_name: str
    old_value: str | None  # for modified
    new_value: str | None  # for modified
    path: str  # breadcrumb path

@dataclass
class TreeDiff:
    added: list[ElementChange]
    removed: list[ElementChange]
    modified: list[ElementChange]
    summary: str

def diff_trees(before: ElementInfo, after: ElementInfo) -> TreeDiff:
    """Compare two UI trees and return differences."""
    ...

def diff_snapshots(snapshot_id_1: str, snapshot_id_2: str) -> TreeDiff:
    """Compare two snapshots by ID."""
    ...
```

### CLI
```bash
naturo diff --snapshot snap1 --snapshot snap2
naturo diff --window "Notepad" --interval 2  # capture, wait, capture, diff
```

## File Structure

```
naturo/
  errors.py          # 3.1 Error framework
  retry.py           # 3.2 Retry policies
  wait.py            # 3.2 Wait functions
  process.py         # 3.3 Process management
  cache.py           # 3.4 Element cache
  diff.py            # 3.5 UI tree diff
  cli/
    wait_cmd.py      # CLI wait command
    app_cmd.py       # CLI app command (launch/quit/relaunch/list/find)
    diff_cmd.py      # CLI diff command
```

## Test Requirements

Each module gets its own test file:
- `tests/test_errors.py` — Error creation, codes, JSON formatting, context
- `tests/test_retry.py` — Retry policies, exponential backoff, retryable/non-retryable
- `tests/test_wait.py` — Wait polling, timeout, found/not-found
- `tests/test_process.py` — Launch, quit, relaunch, find, is_running
- `tests/test_cache.py` — TTL, invalidation, stale detection
- `tests/test_diff.py` — Tree comparison, added/removed/modified detection
- `tests/test_cli_phase3.py` — CLI integration for all new commands

Windows-only features: use `@pytest.mark.skipif(sys.platform != "win32")` or xfail.

## CI
All 4 platforms must pass (Windows, Ubuntu, macOS, existing + new tests).
