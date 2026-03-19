# Naturo Test Plan

## Test Execution

```bash
# All non-UI tests (runs on macOS/Linux/Windows without a display)
pytest tests/ -m "not ui and not windows and not e2e"

# Full Windows suite (requires Windows + naturo_core.dll)
pytest tests/ --run-ui --run-windows

# With coverage
pytest tests/ --cov=naturo --cov-report=term-missing
```

---

## Phase 0 — Foundation

| ID | Description | File | Priority |
|----|-------------|------|----------|
| P0-01 | Version string matches `__version__` | `test_version.py` | P0 |
| P0-02 | Python 3.9–3.13 compatibility | `test_python_compat.py` | P0 |
| P0-03 | Version consistency across package | `test_version_consistency.py` | P0 |

---

## Phase 1 — See (Capture + List + See)

| ID | Description | File | Priority |
|----|-------------|------|----------|
| P1-01 | `capture live` saves screenshot on Windows | `test_capture.py` | P1 |
| P1-02 | `list windows` returns window list on Windows | `test_list_windows.py` | P1 |
| P1-03 | `see` returns element tree on Windows | `test_element_tree.py` | P1 |
| P1-04 | Backend selector picks correct platform backend | `test_backends.py` | P1 |
| P1-05 | Selector engine parses CSS-like queries | `test_selector.py` | P1 |

---

## Phase 1.5 — Snapshot System

Aligned with Peekaboo's `UIAutomationSnapshot` / `SnapshotManager` architecture.
Storage: `~/.naturo/snapshots/<snapshot_id>/` (atomic JSON, thread-safe).

### Data Model (`tests/test_snapshot.py`)

| ID | Description | Class | Priority |
|----|-------------|-------|----------|
| P1.5-01 | `UIElement.to_dict()` / `from_dict()` round-trip preserves all fields | `TestJSONRoundTrip` | P1.5 |
| P1.5-02 | Optional UIElement fields survive None round-trip | `TestJSONRoundTrip` | P1.5 |
| P1.5-03 | `Snapshot.to_json()` / `from_json()` full round-trip | `TestJSONRoundTrip` | P1.5 |
| P1.5-04 | Snapshot without optional fields serialises/restores cleanly | `TestJSONRoundTrip` | P1.5 |
| P1.5-05 | Full persist → load via SnapshotManager (integration) | `TestJSONRoundTrip` | P1.5 |

### SnapshotManager — create (`tests/test_snapshot.py`)

| ID | Description | Class | Priority |
|----|-------------|-------|----------|
| P1.5-06 | `create_snapshot()` returns a non-empty string ID | `TestCreateSnapshot` | P1.5 |
| P1.5-07 | Snapshot ID has `<ms>-<suffix>` format | `TestCreateSnapshot` | P1.5 |
| P1.5-08 | Creates snapshot directory on disk | `TestCreateSnapshot` | P1.5 |
| P1.5-09 | Creates valid skeleton `snapshot.json` | `TestCreateSnapshot` | P1.5 |
| P1.5-10 | 10 consecutive calls produce unique IDs | `TestCreateSnapshot` | P1.5 |

### SnapshotManager — store_screenshot (`tests/test_snapshot.py`)

| ID | Description | Class | Priority |
|----|-------------|-------|----------|
| P1.5-11 | Copies screenshot file to `raw.png` | `TestStoreScreenshot` | P1.5 |
| P1.5-12 | Updates `screenshot_path` in persisted JSON | `TestStoreScreenshot` | P1.5 |
| P1.5-13 | Persists all metadata fields | `TestStoreScreenshot` | P1.5 |
| P1.5-14 | Raises `SnapshotStorageError` for missing source file | `TestStoreScreenshot` | P1.5 |

### SnapshotManager — store_detection_result (`tests/test_snapshot.py`)

| ID | Description | Class | Priority |
|----|-------------|-------|----------|
| P1.5-15 | Persists ui_map to JSON | `TestStoreDetectionResult` | P1.5 |
| P1.5-16 | All UIElement fields survive persist → load | `TestStoreDetectionResult` | P1.5 |
| P1.5-17 | Second call replaces previous ui_map | `TestStoreDetectionResult` | P1.5 |

### SnapshotManager — store_annotated (`tests/test_snapshot.py`)

| ID | Description | Class | Priority |
|----|-------------|-------|----------|
| P1.5-18 | Copies annotated screenshot to `annotated.png` | `TestStoreAnnotated` | P1.5 |
| P1.5-19 | Updates `annotated_path` in persisted JSON | `TestStoreAnnotated` | P1.5 |
| P1.5-20 | Raises `SnapshotStorageError` for missing source | `TestStoreAnnotated` | P1.5 |

### SnapshotManager — get_snapshot (`tests/test_snapshot.py`)

| ID | Description | Class | Priority |
|----|-------------|-------|----------|
| P1.5-21 | Raises `SnapshotNotFoundError` for unknown ID | `TestGetSnapshot` | P1.5 |
| P1.5-22 | Raises `SnapshotVersionError` on schema mismatch | `TestGetSnapshot` | P1.5 |
| P1.5-23 | Loads full snapshot with correct fields | `TestGetSnapshot` | P1.5 |

### SnapshotManager — get_most_recent_snapshot (`tests/test_snapshot.py`)

| ID | Description | Class | Priority |
|----|-------------|-------|----------|
| P1.5-24 | Returns `None` when storage is empty | `TestGetMostRecentSnapshot` | P1.5 |
| P1.5-25 | Returns ID of a fresh snapshot | `TestGetMostRecentSnapshot` | P1.5 |
| P1.5-26 | Returns `None` for expired snapshot (validity=0s) | `TestGetMostRecentSnapshot` | P1.5 |
| P1.5-27 | Returns the newest of two valid snapshots | `TestGetMostRecentSnapshot` | P1.5 |
| P1.5-28 | Filters by `app_name` (exact substring) | `TestGetMostRecentSnapshot` | P1.5 |
| P1.5-29 | `app_name` filter is case-insensitive | `TestGetMostRecentSnapshot` | P1.5 |

### SnapshotManager — list_snapshots (`tests/test_snapshot.py`)

| ID | Description | Class | Priority |
|----|-------------|-------|----------|
| P1.5-30 | Returns empty list when storage is empty | `TestListSnapshots` | P1.5 |
| P1.5-31 | Returns all created snapshots | `TestListSnapshots` | P1.5 |
| P1.5-32 | List sorted newest first | `TestListSnapshots` | P1.5 |
| P1.5-33 | `screenshot_count` reflects actual PNG files | `TestListSnapshots` | P1.5 |
| P1.5-34 | `application_name` populated from metadata | `TestListSnapshots` | P1.5 |
| P1.5-35 | Returns `SnapshotInfo` instances | `TestListSnapshots` | P1.5 |

### SnapshotManager — clean_snapshot (`tests/test_snapshot.py`)

| ID | Description | Class | Priority |
|----|-------------|-------|----------|
| P1.5-36 | Removes snapshot directory | `TestCleanSnapshot` | P1.5 |
| P1.5-37 | No error when snapshot does not exist | `TestCleanSnapshot` | P1.5 |
| P1.5-38 | `get_snapshot` raises after clean | `TestCleanSnapshot` | P1.5 |

### SnapshotManager — clean_older_than (`tests/test_snapshot.py`)

| ID | Description | Class | Priority |
|----|-------------|-------|----------|
| P1.5-39 | Fresh snapshots are not deleted | `TestCleanOlderThan` | P1.5 |
| P1.5-40 | Backdated snapshots are deleted | `TestCleanOlderThan` | P1.5 |
| P1.5-41 | Returns count of deleted snapshots | `TestCleanOlderThan` | P1.5 |

### SnapshotManager — clean_all (`tests/test_snapshot.py`)

| ID | Description | Class | Priority |
|----|-------------|-------|----------|
| P1.5-42 | Removes all snapshots | `TestCleanAll` | P1.5 |
| P1.5-43 | Returns count | `TestCleanAll` | P1.5 |
| P1.5-44 | Safe on empty storage | `TestCleanAll` | P1.5 |

### Thread Safety (`tests/test_snapshot.py`)

| ID | Description | Class | Priority |
|----|-------------|-------|----------|
| P1.5-45 | 20 concurrent `create_snapshot()` produce unique IDs with no errors | `TestThreadSafety` | P1.5 |
| P1.5-46 | Concurrent readers and writers do not corrupt snapshot data | `TestThreadSafety` | P1.5 |

### Atomic Write (`tests/test_snapshot.py`)

| ID | Description | Class | Priority |
|----|-------------|-------|----------|
| P1.5-47 | Skeleton JSON is fully readable immediately after `create_snapshot()` | `TestAtomicWrite` | P1.5 |

### storage_path property (`tests/test_snapshot.py`)

| ID | Description | Class | Priority |
|----|-------------|-------|----------|
| P1.5-48 | `storage_path` matches configured root | `TestStoragePath` | P1.5 |

**Phase 1.5 total: 48 tests (all automated, platform-independent)**

---

## Phase 2 — Interact (Click + Type + Press)

| ID | Description | File | Priority |
|----|-------------|------|----------|
| P2-01 | `click` dispatches correct coordinates | `test_cli_phase2.py` | P2 |
| P2-02 | `type` sends text via SendInput | `test_input_keyboard.py` | P2 |
| P2-03 | `press ctrl+s` sends correct VK codes | `test_input_keyboard.py` | P2 |
| P2-04 | `scroll` sends wheel events | `test_input_mouse.py` | P2 |
| P2-05 | `drag` sends correct mouse sequence | `test_input_mouse.py` | P2 |
| P2-06 | Menu navigation works end-to-end | `test_menu_system.py` | P2 |
| P2-07 | Clipboard read/write round-trip | `test_clipboard.py` | P2 |
| P2-08 | `app launch/close` works | `test_app_control.py` | P2 |
| P2-09 | Security validation rejects invalid input | `test_security.py` | P2 |

---

## Phase 3 — AI Agent + MCP

| ID | Description | File | Priority |
|----|-------------|------|----------|
| P3-01 | `agent` command calls AI provider | TBD | P3 |
| P3-02 | MCP server starts and accepts tool calls | TBD | P3 |
| P3-03 | AI vision identifies UI elements from screenshot | TBD | P3 |
| P3-04 | End-to-end: agent fills a form in Notepad | TBD | P3 |

---

## Notes

- Tests marked `@pytest.mark.ui` require a live Windows desktop session.
- Tests marked `@pytest.mark.windows` require Windows + `naturo_core.dll`.
- Phase 1.5 snapshot tests run on **all platforms** (no Windows dependency).
- CI matrix: `ubuntu-latest` + `macos-latest` run Python-only; `windows-latest`
  runs the full stack.
