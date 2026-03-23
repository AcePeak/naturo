"""Tests for the Phase 1.5 Snapshot System.

Covers:
- SnapshotManager create / store / load round-trip
- Screenshot and annotated-screenshot storage
- ui_map persistence via store_detection_result
- Validity-window filtering in get_most_recent_snapshot
- app_name filter in get_most_recent_snapshot
- list_snapshots ordering and content
- clean_snapshot, clean_older_than, clean_all
- Thread-safety (concurrent creates)
- JSON serialisation / deserialisation for UIElement and Snapshot
- SnapshotVersionError on schema mismatch
- SnapshotNotFoundError for missing IDs

All tests use a temporary directory so they never touch ~/.naturo.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict
from unittest.mock import patch

import pytest

from naturo.models.snapshot import (
    Snapshot,
    SnapshotInfo,
    SnapshotNotFoundError,
    SnapshotStorageError,
    SnapshotVersionError,
    UIElement,
)
from naturo.snapshot import SnapshotManager


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture()
def tmp_root(tmp_path: Path) -> Path:
    """Isolated snapshot storage root."""
    root = tmp_path / "snapshots"
    root.mkdir()
    return root


@pytest.fixture()
def mgr(tmp_root: Path) -> SnapshotManager:
    """SnapshotManager backed by a temporary directory."""
    return SnapshotManager(storage_root=tmp_root)


@pytest.fixture()
def sample_element() -> UIElement:
    return UIElement(
        id="e1",
        element_id="element_0",
        role="AXButton",
        title="Save",
        label="Save",
        value=None,
        frame=(10, 20, 80, 30),
        is_actionable=True,
        parent_id=None,
        children=[],
        keyboard_shortcut="Ctrl+S",
    )


@pytest.fixture()
def sample_ui_map(sample_element: UIElement) -> Dict[str, UIElement]:
    edit = UIElement(
        id="e2",
        element_id="element_1",
        role="AXTextField",
        title="Filename",
        label="Filename",
        value="document.txt",
        frame=(100, 50, 200, 25),
        is_actionable=True,
        parent_id=None,
        children=[],
    )
    return {"e1": sample_element, "e2": edit}


@pytest.fixture()
def png_file(tmp_path: Path) -> Path:
    """Tiny valid PNG file for screenshot tests."""
    # 1×1 white PNG (minimal valid PNG bytes)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"  # signature
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02"
        b"\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    p = tmp_path / "test.png"
    p.write_bytes(png_bytes)
    return p


# ── create_snapshot ───────────────────────────────────────────────────────────


class TestCreateSnapshot:
    def test_returns_string_id(self, mgr: SnapshotManager) -> None:
        sid = mgr.create_snapshot()
        assert isinstance(sid, str)
        assert len(sid) > 0

    def test_id_format(self, mgr: SnapshotManager) -> None:
        """ID is <unix-ms>-<suffix> format."""
        sid = mgr.create_snapshot()
        parts = sid.split("-")
        assert len(parts) == 2
        assert parts[0].isdigit()

    def test_creates_directory(self, mgr: SnapshotManager, tmp_root: Path) -> None:
        sid = mgr.create_snapshot()
        assert (tmp_root / sid).is_dir()

    def test_creates_skeleton_json(self, mgr: SnapshotManager, tmp_root: Path) -> None:
        sid = mgr.create_snapshot()
        json_path = tmp_root / sid / "snapshot.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["snapshotId"] == sid

    def test_unique_ids(self, mgr: SnapshotManager) -> None:
        ids = {mgr.create_snapshot() for _ in range(10)}
        assert len(ids) == 10


# ── store_screenshot ──────────────────────────────────────────────────────────


class TestStoreScreenshot:
    def test_copies_file(self, mgr: SnapshotManager, tmp_root: Path, png_file: Path) -> None:
        sid = mgr.create_snapshot()
        mgr.store_screenshot(sid, str(png_file))
        assert (tmp_root / sid / "raw.png").exists()

    def test_updates_screenshot_path_in_json(
        self, mgr: SnapshotManager, tmp_root: Path, png_file: Path
    ) -> None:
        sid = mgr.create_snapshot()
        mgr.store_screenshot(sid, str(png_file))
        snapshot = mgr.get_snapshot(sid)
        assert snapshot.screenshot_path is not None
        assert "raw.png" in snapshot.screenshot_path

    def test_stores_metadata(self, mgr: SnapshotManager, png_file: Path) -> None:
        sid = mgr.create_snapshot()
        meta = {
            "application_name": "Notepad",
            "application_pid": 1234,
            "window_title": "Untitled",
            "window_bounds": (0, 0, 800, 600),
            "window_handle": 999,
        }
        mgr.store_screenshot(sid, str(png_file), meta)
        snap = mgr.get_snapshot(sid)
        assert snap.application_name == "Notepad"
        assert snap.application_pid == 1234
        assert snap.window_title == "Untitled"
        assert snap.window_bounds == (0, 0, 800, 600)
        assert snap.window_handle == 999

    def test_raises_on_missing_source(self, mgr: SnapshotManager) -> None:
        sid = mgr.create_snapshot()
        with pytest.raises(SnapshotStorageError):
            mgr.store_screenshot(sid, "/nonexistent/path/image.png")


# ── store_detection_result ────────────────────────────────────────────────────


class TestStoreDetectionResult:
    def test_persists_ui_map(
        self,
        mgr: SnapshotManager,
        sample_ui_map: Dict[str, UIElement],
    ) -> None:
        sid = mgr.create_snapshot()
        mgr.store_detection_result(sid, sample_ui_map)
        snap = mgr.get_snapshot(sid)
        assert len(snap.ui_map) == 2

    def test_element_fields_round_trip(
        self,
        mgr: SnapshotManager,
        sample_element: UIElement,
    ) -> None:
        sid = mgr.create_snapshot()
        mgr.store_detection_result(sid, {"e1": sample_element})
        snap = mgr.get_snapshot(sid)
        el = snap.ui_map["e1"]
        assert el.id == "e1"
        assert el.role == "AXButton"
        assert el.title == "Save"
        assert el.frame == (10, 20, 80, 30)
        assert el.is_actionable is True
        assert el.keyboard_shortcut == "Ctrl+S"

    def test_replaces_existing_map(
        self,
        mgr: SnapshotManager,
        sample_ui_map: Dict[str, UIElement],
    ) -> None:
        sid = mgr.create_snapshot()
        mgr.store_detection_result(sid, sample_ui_map)
        # Store only one element
        single = {"e1": sample_ui_map["e1"]}
        mgr.store_detection_result(sid, single)
        snap = mgr.get_snapshot(sid)
        assert len(snap.ui_map) == 1


# ── store_annotated ───────────────────────────────────────────────────────────


class TestStoreAnnotated:
    def test_copies_annotated(
        self, mgr: SnapshotManager, tmp_root: Path, png_file: Path
    ) -> None:
        sid = mgr.create_snapshot()
        mgr.store_annotated(sid, str(png_file))
        assert (tmp_root / sid / "annotated.png").exists()

    def test_updates_annotated_path(
        self, mgr: SnapshotManager, png_file: Path
    ) -> None:
        sid = mgr.create_snapshot()
        mgr.store_annotated(sid, str(png_file))
        snap = mgr.get_snapshot(sid)
        assert snap.annotated_path is not None
        assert "annotated.png" in snap.annotated_path

    def test_raises_on_missing_source(self, mgr: SnapshotManager) -> None:
        sid = mgr.create_snapshot()
        with pytest.raises(SnapshotStorageError):
            mgr.store_annotated(sid, "/nonexistent/annotated.png")


# ── get_snapshot ──────────────────────────────────────────────────────────────


class TestGetSnapshot:
    def test_raises_for_unknown_id(self, mgr: SnapshotManager) -> None:
        with pytest.raises(SnapshotNotFoundError):
            mgr.get_snapshot("no-such-id")

    def test_raises_version_mismatch(self, mgr: SnapshotManager, tmp_root: Path) -> None:
        sid = mgr.create_snapshot()
        json_path = tmp_root / sid / "snapshot.json"
        data = json.loads(json_path.read_text(encoding="utf-8"))
        data["version"] = 999
        json_path.write_text(json.dumps(data))
        with pytest.raises(SnapshotVersionError):
            mgr.get_snapshot(sid)

    def test_loads_full_snapshot(
        self,
        mgr: SnapshotManager,
        sample_ui_map: Dict[str, UIElement],
    ) -> None:
        sid = mgr.create_snapshot()
        mgr.store_detection_result(sid, sample_ui_map)
        snap = mgr.get_snapshot(sid)
        assert snap.snapshot_id == sid
        assert snap.version == 1
        assert len(snap.ui_map) == 2


# ── get_most_recent_snapshot ──────────────────────────────────────────────────


class TestGetMostRecentSnapshot:
    def test_returns_none_when_empty(self, mgr: SnapshotManager) -> None:
        assert mgr.get_most_recent_snapshot() is None

    def test_returns_id_of_fresh_snapshot(self, mgr: SnapshotManager) -> None:
        sid = mgr.create_snapshot()
        assert mgr.get_most_recent_snapshot() == sid

    def test_returns_none_for_expired_snapshot(
        self, tmp_root: Path
    ) -> None:
        # Very short validity window
        mgr = SnapshotManager(storage_root=tmp_root, validity_seconds=0)
        mgr.create_snapshot()
        time.sleep(0.01)
        assert mgr.get_most_recent_snapshot() is None

    def test_returns_most_recent_of_two(self, mgr: SnapshotManager) -> None:
        sid1 = mgr.create_snapshot()
        time.sleep(0.02)  # ensure different mtime
        sid2 = mgr.create_snapshot()
        result = mgr.get_most_recent_snapshot()
        assert result == sid2

    def test_filters_by_app_name(
        self, mgr: SnapshotManager, png_file: Path
    ) -> None:
        sid_notepad = mgr.create_snapshot()
        mgr.store_screenshot(sid_notepad, str(png_file), {"application_name": "Notepad"})
        sid_calc = mgr.create_snapshot()
        mgr.store_screenshot(sid_calc, str(png_file), {"application_name": "Calculator"})

        assert mgr.get_most_recent_snapshot(app_name="Notepad") == sid_notepad
        assert mgr.get_most_recent_snapshot(app_name="Calculator") == sid_calc
        assert mgr.get_most_recent_snapshot(app_name="NoSuchApp") is None

    def test_app_name_case_insensitive(
        self, mgr: SnapshotManager, png_file: Path
    ) -> None:
        sid = mgr.create_snapshot()
        mgr.store_screenshot(sid, str(png_file), {"application_name": "Notepad"})
        assert mgr.get_most_recent_snapshot(app_name="notepad") == sid
        assert mgr.get_most_recent_snapshot(app_name="NOTE") == sid


# ── list_snapshots ────────────────────────────────────────────────────────────


class TestListSnapshots:
    def test_empty_returns_empty_list(self, mgr: SnapshotManager) -> None:
        assert mgr.list_snapshots() == []

    def test_returns_all_created(self, mgr: SnapshotManager) -> None:
        ids = {mgr.create_snapshot() for _ in range(3)}
        infos = mgr.list_snapshots()
        assert {s.id for s in infos} == ids

    def test_sorted_newest_first(self, mgr: SnapshotManager) -> None:
        sids = []
        for _ in range(3):
            sids.append(mgr.create_snapshot())
            time.sleep(0.01)
        infos = mgr.list_snapshots()
        assert infos[0].id == sids[-1]

    def test_includes_screenshot_count(
        self, mgr: SnapshotManager, png_file: Path
    ) -> None:
        sid = mgr.create_snapshot()
        mgr.store_screenshot(sid, str(png_file))
        infos = mgr.list_snapshots()
        info = next(i for i in infos if i.id == sid)
        assert info.screenshot_count >= 1

    def test_includes_app_name(
        self, mgr: SnapshotManager, png_file: Path
    ) -> None:
        sid = mgr.create_snapshot()
        mgr.store_screenshot(sid, str(png_file), {"application_name": "Notepad"})
        infos = mgr.list_snapshots()
        info = next(i for i in infos if i.id == sid)
        assert info.application_name == "Notepad"

    def test_snapshot_info_type(self, mgr: SnapshotManager) -> None:
        mgr.create_snapshot()
        infos = mgr.list_snapshots()
        assert all(isinstance(i, SnapshotInfo) for i in infos)


# ── clean_snapshot ────────────────────────────────────────────────────────────


class TestCleanSnapshot:
    def test_removes_directory(self, mgr: SnapshotManager, tmp_root: Path) -> None:
        sid = mgr.create_snapshot()
        assert (tmp_root / sid).exists()
        mgr.clean_snapshot(sid)
        assert not (tmp_root / sid).exists()

    def test_no_error_on_missing(self, mgr: SnapshotManager) -> None:
        mgr.clean_snapshot("nonexistent-snapshot")  # should not raise

    def test_snapshot_gone_after_clean(self, mgr: SnapshotManager) -> None:
        sid = mgr.create_snapshot()
        mgr.clean_snapshot(sid)
        with pytest.raises(SnapshotNotFoundError):
            mgr.get_snapshot(sid)


# ── clean_older_than ──────────────────────────────────────────────────────────


class TestCleanOlderThan:
    def test_keeps_fresh_snapshots(self, mgr: SnapshotManager) -> None:
        sid = mgr.create_snapshot()
        deleted = mgr.clean_older_than(days=1)
        assert deleted == 0
        assert mgr.get_snapshot(sid) is not None

    def test_deletes_old_snapshots(self, tmp_root: Path) -> None:
        mgr = SnapshotManager(storage_root=tmp_root)
        sid = mgr.create_snapshot()
        snap_dir = tmp_root / sid

        # Backdate the directory mtime to 2 days ago
        old_time = time.time() - 2 * 86400
        os.utime(snap_dir, (old_time, old_time))

        deleted = mgr.clean_older_than(days=1)
        assert deleted == 1
        assert not snap_dir.exists()

    def test_returns_count(self, tmp_root: Path) -> None:
        import os as _os
        mgr = SnapshotManager(storage_root=tmp_root)
        for _ in range(3):
            sid = mgr.create_snapshot()
            snap_dir = tmp_root / sid
            old_time = time.time() - 5 * 86400
            _os.utime(snap_dir, (old_time, old_time))
        assert mgr.clean_older_than(days=1) == 3


# ── clean_all ─────────────────────────────────────────────────────────────────


class TestCleanAll:
    def test_removes_all(self, mgr: SnapshotManager) -> None:
        for _ in range(5):
            mgr.create_snapshot()
        count = mgr.clean_all()
        assert count == 5
        assert mgr.list_snapshots() == []

    def test_returns_count(self, mgr: SnapshotManager) -> None:
        for _ in range(3):
            mgr.create_snapshot()
        assert mgr.clean_all() == 3

    def test_empty_root(self, mgr: SnapshotManager) -> None:
        assert mgr.clean_all() == 0


# ── Thread-safety ─────────────────────────────────────────────────────────────


class TestThreadSafety:
    def test_concurrent_creates(self, mgr: SnapshotManager) -> None:
        results = []
        errors = []

        def worker():
            try:
                sid = mgr.create_snapshot()
                results.append(sid)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Concurrent create raised: {errors}"
        assert len(set(results)) == 20, "Expected 20 unique snapshot IDs"

    def test_concurrent_read_write(
        self, mgr: SnapshotManager, sample_ui_map: Dict[str, UIElement]
    ) -> None:
        """Writers and readers should not corrupt data."""
        sid = mgr.create_snapshot()
        errors = []

        def writer():
            try:
                for _ in range(5):
                    mgr.store_detection_result(sid, sample_ui_map)
            except Exception as exc:
                errors.append(exc)

        def reader():
            try:
                for _ in range(5):
                    try:
                        mgr.get_snapshot(sid)
                    except (SnapshotNotFoundError, SnapshotStorageError):
                        pass  # race is acceptable; corruption is not
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer) for _ in range(4)]
        threads += [threading.Thread(target=reader) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []


# ── JSON serialisation / deserialisation ──────────────────────────────────────


class TestJSONRoundTrip:
    def test_ui_element_round_trip(self, sample_element: UIElement) -> None:
        d = sample_element.to_dict()
        restored = UIElement.from_dict(d)
        assert restored.id == sample_element.id
        assert restored.role == sample_element.role
        assert restored.frame == sample_element.frame
        assert restored.is_actionable == sample_element.is_actionable
        assert restored.keyboard_shortcut == sample_element.keyboard_shortcut

    def test_ui_element_optional_fields_none(self) -> None:
        el = UIElement(id="x", element_id="element_0", role="AXGroup")
        d = el.to_dict()
        restored = UIElement.from_dict(d)
        assert restored.title is None
        assert restored.label is None
        assert restored.parent_id is None
        assert restored.children == []

    def test_snapshot_round_trip(self, sample_ui_map: Dict[str, UIElement]) -> None:
        snap = Snapshot(
            snapshot_id="test-snap-001",
            screenshot_path="/tmp/raw.png",
            annotated_path="/tmp/annotated.png",
            ui_map=sample_ui_map,
            last_update_time=datetime(2025, 1, 1, 12, 0, 0),
            application_name="Notepad",
            application_pid=9999,
            window_title="test.txt",
            window_bounds=(0, 0, 1920, 1080),
            window_handle=12345,
        )
        json_str = snap.to_json()
        restored = Snapshot.from_json(json_str)

        assert restored.snapshot_id == "test-snap-001"
        assert restored.screenshot_path == "/tmp/raw.png"
        assert restored.application_name == "Notepad"
        assert restored.application_pid == 9999
        assert restored.window_bounds == (0, 0, 1920, 1080)
        assert restored.window_handle == 12345
        assert len(restored.ui_map) == 2

    def test_snapshot_without_optional_fields(self) -> None:
        snap = Snapshot(snapshot_id="minimal")
        restored = Snapshot.from_json(snap.to_json())
        assert restored.snapshot_id == "minimal"
        assert restored.screenshot_path is None
        assert restored.window_bounds is None
        assert restored.ui_map == {}

    def test_snapshot_persist_load_via_manager(
        self,
        mgr: SnapshotManager,
        sample_ui_map: Dict[str, UIElement],
        png_file: Path,
    ) -> None:
        sid = mgr.create_snapshot()
        mgr.store_detection_result(sid, sample_ui_map)
        mgr.store_screenshot(
            sid,
            str(png_file),
            {"application_name": "TestApp", "window_bounds": (10, 20, 800, 600)},
        )
        snap = mgr.get_snapshot(sid)
        assert snap.application_name == "TestApp"
        assert snap.window_bounds == (10, 20, 800, 600)
        assert "e1" in snap.ui_map
        assert "e2" in snap.ui_map


# ── Atomic write ──────────────────────────────────────────────────────────────


class TestAtomicWrite:
    def test_no_partial_file_visible(self, mgr: SnapshotManager, tmp_root: Path) -> None:
        """After create_snapshot the JSON must be fully readable."""
        sid = mgr.create_snapshot()
        json_path = tmp_root / sid / "snapshot.json"
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["snapshotId"] == sid


# ── storage_path property ─────────────────────────────────────────────────────


class TestStoragePath:
    def test_returns_correct_path(self, mgr: SnapshotManager, tmp_root: Path) -> None:
        assert Path(mgr.storage_path) == tmp_root


# ── need os for backdate test ─────────────────────────────────────────────────
import os  # noqa: E402  (placed here intentionally to keep test-only import)
