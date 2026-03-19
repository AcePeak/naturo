"""SnapshotManager — thread-safe snapshot storage aligned with Peekaboo's SnapshotManager.

Storage layout::

    ~/.naturo/snapshots/
    └── <snapshot_id>/          # e.g. 1742363045123-7321
        ├── snapshot.json       # full Snapshot serialisation
        ├── raw.png             # copied raw screenshot (optional)
        └── annotated.png       # annotated screenshot (optional)

Design notes
------------
* **Atomic writes** — JSON is written to a temp file in the same directory, then
  ``os.replace()``-d into place, so readers never see partial data.
* **Thread safety** — a single :class:`threading.Lock` guards all mutations.
  For async callers, wrap calls in ``asyncio.get_event_loop().run_in_executor``.
* **Snapshot ID format** — ``<unix-ms>-<4-digit-random>`` for easy chronological sorting
  without a UUID dependency.
* **Validity window** — 10 minutes, matching Peekaboo's ``snapshotValidityWindow``.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from naturo.models.snapshot import (
    Snapshot,
    SnapshotInfo,
    SnapshotNotFoundError,
    SnapshotStorageError,
    SnapshotVersionError,
    UIElement,
)

logger = logging.getLogger(__name__)

#: Snapshot validity window — matches Peekaboo (10 minutes).
SNAPSHOT_VALIDITY_SECONDS: int = 600

#: Default storage root.
DEFAULT_STORAGE_ROOT: Path = Path.home() / ".naturo" / "snapshots"


class SnapshotManager:
    """Manages snapshot lifecycle: create, store, load, query, and clean.

    Parameters
    ----------
    storage_root:
        Override the default storage path (``~/.naturo/snapshots``).
        Useful for testing.
    validity_seconds:
        How old a snapshot may be before :meth:`get_most_recent_snapshot`
        ignores it.  Defaults to 600 s (10 minutes).
    """

    def __init__(
        self,
        storage_root: Optional[Path] = None,
        validity_seconds: int = SNAPSHOT_VALIDITY_SECONDS,
    ) -> None:
        self._root = Path(storage_root) if storage_root else DEFAULT_STORAGE_ROOT
        self._validity_seconds = validity_seconds
        self._lock = threading.Lock()
        self._root.mkdir(parents=True, exist_ok=True)

    # ── Public API ───────────────────────────────────────────────────────────

    def create_snapshot(self) -> str:
        """Generate a new snapshot ID and initialise its storage directory.

        Returns
        -------
        str
            The new snapshot ID (``"<unix-ms>-<4-digit-random>"``).
        """
        ts_ms = int(time.time() * 1000)
        suffix = str(uuid.uuid4().int)[:4]
        snapshot_id = f"{ts_ms}-{suffix}"

        snap_dir = self._snap_dir(snapshot_id)
        with self._lock:
            snap_dir.mkdir(parents=True, exist_ok=True)
            # Write an empty skeleton so the directory is valid immediately.
            skeleton = Snapshot(snapshot_id=snapshot_id)
            self._write_json_atomic(snap_dir / "snapshot.json", skeleton.to_dict())

        logger.debug("Created snapshot: %s", snapshot_id)
        return snapshot_id

    def store_screenshot(
        self,
        snapshot_id: str,
        screenshot_path: str,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Copy a screenshot into the snapshot directory and persist metadata.

        Parameters
        ----------
        snapshot_id:
            Target snapshot.
        screenshot_path:
            Source image file (must exist).
        metadata:
            Optional dict with keys: ``application_name``, ``application_pid``,
            ``window_title``, ``window_bounds`` (4-tuple), ``window_handle``.
        """
        src = Path(screenshot_path)
        if not src.exists():
            raise SnapshotStorageError(f"Screenshot not found: {screenshot_path}")

        snap_dir = self._snap_dir(snapshot_id)
        with self._lock:
            snap_dir.mkdir(parents=True, exist_ok=True)
            snapshot = self._load_or_create(snapshot_id)

            # Copy image
            dst = snap_dir / "raw.png"
            shutil.copy2(src, dst)
            snapshot.screenshot_path = str(dst)

            # Apply metadata
            if metadata:
                snapshot.application_name = metadata.get("application_name", snapshot.application_name)
                snapshot.application_pid = metadata.get("application_pid", snapshot.application_pid)
                snapshot.window_title = metadata.get("window_title", snapshot.window_title)
                snapshot.window_bounds = metadata.get("window_bounds", snapshot.window_bounds)
                snapshot.window_handle = metadata.get("window_handle", snapshot.window_handle)

            snapshot.last_update_time = datetime.utcnow()
            self._write_json_atomic(snap_dir / "snapshot.json", snapshot.to_dict())

        logger.debug("Stored screenshot for snapshot %s → %s", snapshot_id, dst)

    def store_detection_result(
        self,
        snapshot_id: str,
        ui_elements: Dict[str, UIElement],
    ) -> None:
        """Update the ``ui_map`` of an existing snapshot.

        Parameters
        ----------
        snapshot_id:
            Target snapshot.
        ui_elements:
            New element map (replaces any existing ``ui_map``).
        """
        snap_dir = self._snap_dir(snapshot_id)
        with self._lock:
            snapshot = self._load_or_create(snapshot_id)
            snapshot.ui_map = ui_elements
            snapshot.last_update_time = datetime.utcnow()
            self._write_json_atomic(snap_dir / "snapshot.json", snapshot.to_dict())

        logger.debug(
            "Stored detection result for snapshot %s (%d elements)",
            snapshot_id,
            len(ui_elements),
        )

    def store_annotated(self, snapshot_id: str, annotated_path: str) -> None:
        """Copy an annotated screenshot into the snapshot directory.

        Parameters
        ----------
        snapshot_id:
            Target snapshot.
        annotated_path:
            Source annotated image file (must exist).
        """
        src = Path(annotated_path)
        if not src.exists():
            raise SnapshotStorageError(f"Annotated screenshot not found: {annotated_path}")

        snap_dir = self._snap_dir(snapshot_id)
        with self._lock:
            snap_dir.mkdir(parents=True, exist_ok=True)
            snapshot = self._load_or_create(snapshot_id)

            dst = snap_dir / "annotated.png"
            shutil.copy2(src, dst)
            snapshot.annotated_path = str(dst)
            snapshot.last_update_time = datetime.utcnow()
            self._write_json_atomic(snap_dir / "snapshot.json", snapshot.to_dict())

        logger.debug("Stored annotated screenshot for snapshot %s → %s", snapshot_id, dst)

    def get_snapshot(self, snapshot_id: str) -> Snapshot:
        """Load and return a snapshot by ID.

        Raises
        ------
        SnapshotNotFoundError
            If the snapshot directory or ``snapshot.json`` does not exist.
        SnapshotVersionError
            If the stored schema version does not match :attr:`Snapshot.CURRENT_VERSION`.
        SnapshotStorageError
            On JSON decode failures.
        """
        snap_dir = self._snap_dir(snapshot_id)
        json_path = snap_dir / "snapshot.json"

        with self._lock:
            if not json_path.exists():
                raise SnapshotNotFoundError(snapshot_id)

            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise SnapshotStorageError(f"Failed to read snapshot {snapshot_id}: {exc}") from exc

            version = data.get("version", 1)
            if version != Snapshot.CURRENT_VERSION:
                raise SnapshotVersionError(found=version, expected=Snapshot.CURRENT_VERSION)

            return Snapshot.from_dict(data)

    def get_most_recent_snapshot(self, app_name: Optional[str] = None) -> Optional[str]:
        """Return the ID of the most recent valid snapshot within the validity window.

        Parameters
        ----------
        app_name:
            If provided, only consider snapshots whose ``application_name``
            matches (case-insensitive substring match).

        Returns
        -------
        str | None
            The snapshot ID, or ``None`` if no valid snapshot exists.
        """
        cutoff = datetime.utcnow() - timedelta(seconds=self._validity_seconds)
        candidates: List[tuple] = []  # (mtime, snapshot_id)

        with self._lock:
            if not self._root.exists():
                return None

            for entry in self._root.iterdir():
                if not entry.is_dir():
                    continue
                json_path = entry / "snapshot.json"
                if not json_path.exists():
                    continue

                try:
                    mtime = datetime.utcfromtimestamp(entry.stat().st_mtime)
                except OSError:
                    continue

                if mtime < cutoff:
                    continue

                snapshot_id = entry.name

                # Filter by app name if requested
                if app_name:
                    try:
                        data = json.loads(json_path.read_text(encoding="utf-8"))
                        stored_app = data.get("applicationName") or ""
                        if app_name.lower() not in stored_app.lower():
                            continue
                    except (OSError, json.JSONDecodeError):
                        continue

                candidates.append((mtime, snapshot_id))

        if not candidates:
            logger.debug("No valid snapshots found within %ds window", self._validity_seconds)
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        best = candidates[0][1]
        logger.debug("Most recent valid snapshot: %s", best)
        return best

    def list_snapshots(self) -> List[SnapshotInfo]:
        """Return summary information for all stored snapshots, newest first."""
        infos: List[SnapshotInfo] = []

        with self._lock:
            if not self._root.exists():
                return infos

            for entry in self._root.iterdir():
                if not entry.is_dir():
                    continue
                snapshot_id = entry.name
                json_path = entry / "snapshot.json"

                try:
                    stat = entry.stat()
                    created_at = datetime.utcfromtimestamp(stat.st_ctime)
                except OSError:
                    continue

                last_accessed = created_at
                app_name: Optional[str] = None

                if json_path.exists():
                    try:
                        data = json.loads(json_path.read_text(encoding="utf-8"))
                        lu_raw = data.get("lastUpdateTime")
                        if lu_raw:
                            last_accessed = datetime.fromisoformat(str(lu_raw).rstrip("Z"))
                        app_name = data.get("applicationName")
                    except (OSError, json.JSONDecodeError, ValueError):
                        pass

                size_bytes = self._dir_size(entry)
                png_count = sum(1 for f in entry.iterdir() if f.suffix == ".png")

                infos.append(
                    SnapshotInfo(
                        id=snapshot_id,
                        created_at=created_at,
                        last_accessed_at=last_accessed,
                        size_in_bytes=size_bytes,
                        screenshot_count=png_count,
                        application_name=app_name,
                    )
                )

        infos.sort(key=lambda s: s.created_at, reverse=True)
        return infos

    def clean_snapshot(self, snapshot_id: str) -> None:
        """Delete a single snapshot directory.

        Silently succeeds if the snapshot does not exist.
        """
        snap_dir = self._snap_dir(snapshot_id)
        with self._lock:
            if snap_dir.exists():
                shutil.rmtree(snap_dir)
                logger.info("Cleaned snapshot: %s", snapshot_id)
            else:
                logger.debug("Snapshot %s does not exist, skipping", snapshot_id)

    def clean_older_than(self, days: int) -> int:
        """Delete all snapshots whose directory mtime is older than *days* days.

        Returns
        -------
        int
            Number of snapshots deleted.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        cleaned = 0

        with self._lock:
            if not self._root.exists():
                return 0

            for entry in self._root.iterdir():
                if not entry.is_dir():
                    continue
                try:
                    mtime = datetime.utcfromtimestamp(entry.stat().st_mtime)
                except OSError:
                    continue

                if mtime < cutoff:
                    shutil.rmtree(entry)
                    logger.info("Cleaned old snapshot: %s", entry.name)
                    cleaned += 1

        return cleaned

    def clean_all(self) -> int:
        """Delete every snapshot in the storage directory.

        Returns
        -------
        int
            Number of snapshots deleted.
        """
        cleaned = 0
        with self._lock:
            if not self._root.exists():
                return 0
            for entry in self._root.iterdir():
                if entry.is_dir():
                    shutil.rmtree(entry)
                    cleaned += 1

        logger.info("Cleaned all %d snapshots", cleaned)
        return cleaned

    @property
    def storage_path(self) -> str:
        """Absolute path to the snapshot storage root."""
        return str(self._root)

    # ── Private helpers ──────────────────────────────────────────────────────

    def _snap_dir(self, snapshot_id: str) -> Path:
        return self._root / snapshot_id

    def _load_or_create(self, snapshot_id: str) -> Snapshot:
        """Load existing snapshot or create a new skeleton (caller holds lock)."""
        json_path = self._snap_dir(snapshot_id) / "snapshot.json"
        if json_path.exists():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                return Snapshot.from_dict(data)
            except (OSError, json.JSONDecodeError, KeyError):
                pass
        return Snapshot(snapshot_id=snapshot_id)

    @staticmethod
    def _write_json_atomic(path: Path, data: dict) -> None:
        """Write *data* as JSON to *path* atomically (write temp → rename)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        dir_fd = path.parent

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=dir_fd,
            prefix=".tmp_",
            suffix=".json",
            delete=False,
        ) as tmp:
            json.dump(data, tmp, indent=2, ensure_ascii=False)
            tmp_path = tmp.name

        try:
            os.replace(tmp_path, path)
        except OSError:
            os.unlink(tmp_path)
            raise

    @staticmethod
    def _dir_size(path: Path) -> int:
        """Return total byte size of all files under *path*."""
        total = 0
        for f in path.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except OSError:
                    pass
        return total
