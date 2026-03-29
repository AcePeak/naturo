"""Tests for naturo.app_ids — stable app/window ID system (#361)."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

from naturo.app_ids import AppIdEntry, AppIdMap, get_app_id_map


@dataclass
class FakeWindow:
    """Minimal window info for testing."""
    pid: int
    handle: int
    process_name: str
    title: str


@pytest.fixture
def tmp_storage(tmp_path):
    """Provide a temporary storage root for AppIdMap."""
    return tmp_path / "app_ids"


@pytest.fixture
def id_map(tmp_storage):
    """Create an AppIdMap with temp storage."""
    return AppIdMap(session="test", storage_root=tmp_storage)


class TestAppIdMapAssignment:
    """Tests for assign_ids()."""

    def test_assign_sequential_ids(self, id_map):
        windows = [
            FakeWindow(pid=1234, handle=100, process_name="notepad.exe", title="Untitled"),
            FakeWindow(pid=5678, handle=200, process_name="chrome.exe", title="Google"),
        ]
        result = id_map.assign_ids(windows)

        assert "a1" in result
        assert "a2" in result
        assert result["a1"].pid == 1234
        assert result["a1"].handle == 100
        assert result["a1"].process_name == "notepad.exe"
        assert result["a1"].title == "Untitled"
        assert result["a2"].pid == 5678
        assert result["a2"].process_name == "chrome.exe"

    def test_assign_empty_list(self, id_map):
        result = id_map.assign_ids([])
        assert result == {}

    def test_assign_single_window(self, id_map):
        windows = [FakeWindow(pid=1, handle=1, process_name="app.exe", title="App")]
        result = id_map.assign_ids(windows)
        assert len(result) == 1
        assert "a1" in result

    def test_reassign_overwrites_previous(self, id_map):
        """Calling assign_ids again replaces the old map."""
        windows1 = [FakeWindow(pid=1, handle=1, process_name="old.exe", title="Old")]
        id_map.assign_ids(windows1)

        windows2 = [FakeWindow(pid=2, handle=2, process_name="new.exe", title="New")]
        id_map.assign_ids(windows2)

        assert id_map.resolve("a1").process_name == "new.exe"


class TestAppIdMapResolution:
    """Tests for resolve()."""

    def test_resolve_valid_id(self, id_map):
        windows = [
            FakeWindow(pid=1234, handle=100, process_name="notepad.exe", title="Untitled"),
        ]
        id_map.assign_ids(windows)

        entry = id_map.resolve("a1")
        assert entry is not None
        assert entry.pid == 1234
        assert entry.handle == 100

    def test_resolve_unknown_id(self, id_map):
        windows = [FakeWindow(pid=1, handle=1, process_name="a.exe", title="A")]
        id_map.assign_ids(windows)

        assert id_map.resolve("a999") is None

    def test_resolve_expired_id(self, tmp_storage):
        """IDs expire after TTL."""
        id_map = AppIdMap(session="test", storage_root=tmp_storage, ttl_seconds=0)
        windows = [FakeWindow(pid=1, handle=1, process_name="a.exe", title="A")]
        id_map.assign_ids(windows)

        # TTL is 0 so it's already expired
        time.sleep(0.01)
        assert id_map.resolve("a1") is None


class TestAppIdMapPersistence:
    """Tests for persist/load cycle."""

    def test_persist_and_reload(self, tmp_storage):
        """IDs survive across AppIdMap instances."""
        map1 = AppIdMap(session="test", storage_root=tmp_storage)
        windows = [
            FakeWindow(pid=42, handle=999, process_name="excel.exe", title="Sheet1"),
        ]
        map1.assign_ids(windows)

        # New instance with same session — should load from disk
        map2 = AppIdMap(session="test", storage_root=tmp_storage)
        entry = map2.resolve("a1")
        assert entry is not None
        assert entry.pid == 42
        assert entry.handle == 999
        assert entry.process_name == "excel.exe"

    def test_session_isolation(self, tmp_storage):
        """Different sessions have independent ID maps."""
        map_a = AppIdMap(session="session-a", storage_root=tmp_storage)
        map_b = AppIdMap(session="session-b", storage_root=tmp_storage)

        map_a.assign_ids([FakeWindow(pid=1, handle=1, process_name="a.exe", title="A")])
        map_b.assign_ids([FakeWindow(pid=2, handle=2, process_name="b.exe", title="B")])

        assert map_a.resolve("a1").process_name == "a.exe"
        assert map_b.resolve("a1").process_name == "b.exe"

    def test_corrupt_json_handled(self, tmp_storage):
        """Corrupt map file is handled gracefully."""
        tmp_storage.mkdir(parents=True, exist_ok=True)
        (tmp_storage / "test.json").write_text("not valid json")

        id_map = AppIdMap(session="test", storage_root=tmp_storage)
        assert id_map.resolve("a1") is None

    def test_map_file_location(self, tmp_storage):
        """Map file is stored at the expected path."""
        id_map = AppIdMap(session="my-session", storage_root=tmp_storage)
        id_map.assign_ids([FakeWindow(pid=1, handle=1, process_name="a.exe", title="A")])

        expected = tmp_storage / "my-session.json"
        assert expected.exists()


class TestAppIdMapListIds:
    """Tests for list_ids()."""

    def test_list_ids_returns_all(self, id_map):
        windows = [
            FakeWindow(pid=1, handle=1, process_name="a.exe", title="A"),
            FakeWindow(pid=2, handle=2, process_name="b.exe", title="B"),
        ]
        id_map.assign_ids(windows)

        ids = id_map.list_ids()
        assert len(ids) == 2
        assert "a1" in ids
        assert "a2" in ids

    def test_list_ids_empty(self, id_map):
        assert id_map.list_ids() == {}


class TestGetAppIdMap:
    """Tests for the factory function."""

    def test_returns_app_id_map(self):
        result = get_app_id_map(session="factory-test")
        assert isinstance(result, AppIdMap)


class TestResolveAppIdHelper:
    """Tests for the CLI helper _resolve_app_id."""

    def test_passthrough_when_no_app_id(self):
        from naturo.cli.interaction import _resolve_app_id
        app, hwnd, pid = _resolve_app_id(None, "notepad", 123, 456, False)
        assert app == "notepad"
        assert hwnd == 123
        assert pid == 456

    def test_resolve_returns_hwnd_pid_without_app(self, tmp_storage):
        """#573: _resolve_app_id must NOT populate app — only hwnd + pid."""
        from naturo.cli.interaction import _resolve_app_id

        # Set up an ID map
        id_map = AppIdMap(session="default", storage_root=tmp_storage)
        id_map.assign_ids([
            FakeWindow(pid=42, handle=999, process_name="excel.exe", title="Sheet1"),
        ])

        # Monkey-patch get_app_id_map to use our temp storage
        import naturo.app_ids as app_ids_mod
        orig_factory = app_ids_mod.get_app_id_map

        def _patched(session=None):
            return AppIdMap(session=session, storage_root=tmp_storage)

        app_ids_mod.get_app_id_map = _patched
        try:
            app, hwnd, pid = _resolve_app_id("a1", None, None, None, False)
            # (#573) app must be None — process_name may be a full path that
            # breaks fuzzy matching downstream.  hwnd + pid suffice.
            assert app is None
            assert hwnd == 999
            assert pid == 42
        finally:
            app_ids_mod.get_app_id_map = orig_factory

    def test_resolve_full_path_process_name_does_not_leak(self, tmp_storage):
        """#573: Full path in process_name must not become the app filter."""
        from naturo.cli.interaction import _resolve_app_id

        id_map = AppIdMap(session="default", storage_root=tmp_storage)
        id_map.assign_ids([
            FakeWindow(
                pid=100,
                handle=5555,
                process_name=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                title="Google Chrome",
            ),
        ])

        import naturo.app_ids as app_ids_mod
        orig_factory = app_ids_mod.get_app_id_map

        def _patched(session=None):
            return AppIdMap(session=session, storage_root=tmp_storage)

        app_ids_mod.get_app_id_map = _patched
        try:
            app, hwnd, pid = _resolve_app_id("a1", None, None, None, False)
            assert app is None, "app must not be set to full process path"
            assert hwnd == 5555
            assert pid == 100
        finally:
            app_ids_mod.get_app_id_map = orig_factory

    def test_resolve_error_exits(self, tmp_storage):
        """On invalid app_id, _resolve_app_id exits with error."""
        from naturo.cli.interaction import _resolve_app_id

        # Empty storage — no IDs
        import naturo.app_ids as app_ids_mod
        orig_factory = app_ids_mod.get_app_id_map

        def _patched(session=None):
            return AppIdMap(session=session, storage_root=tmp_storage)

        app_ids_mod.get_app_id_map = _patched
        try:
            import pytest
            with pytest.raises(SystemExit):
                _resolve_app_id("a99", None, None, None, False)
        finally:
            app_ids_mod.get_app_id_map = orig_factory
