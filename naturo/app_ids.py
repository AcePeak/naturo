"""AppIdMap — session-scoped stable IDs for apps and windows.

Assigns sequential IDs (a1, a2, ...) to windows discovered by ``naturo app list``.
These IDs can be used in subsequent commands via ``--id a1`` for deterministic
targeting without fuzzy text matching.

Storage layout::

    ~/.naturo/app_ids/
    └── <session>.json          # e.g. "default.json"

The map is regenerated on each ``naturo app list`` call and persists until the
next call or until the TTL expires.

Design follows the same session-isolation pattern as :mod:`naturo.snapshot`.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

logger = logging.getLogger(__name__)

#: Default storage root for app ID maps.
DEFAULT_STORAGE_ROOT: Path = Path.home() / ".naturo" / "app_ids"

#: App ID validity window — 30 minutes (matches snapshot TTL).
APP_ID_TTL_SECONDS: int = 1800

#: Environment variable for overriding app ID TTL (seconds).
APP_ID_TTL_ENV_VAR: str = "NATURO_APP_ID_TTL"

#: Session env var (shared with snapshot.py).
SESSION_ENV_VAR: str = "NATURO_SESSION"

#: Default session name.
DEFAULT_SESSION: str = "default"


@dataclass
class AppIdEntry:
    """A single app/window entry in the ID map."""

    app_id: str
    pid: int
    handle: int
    process_name: str
    title: str
    timestamp: float


class AppIdMap:
    """Manage session-scoped app/window ID assignments.

    Args:
        session: Session name for isolation. Defaults to NATURO_SESSION
            env var or ``"default"``.
        storage_root: Directory for persisted maps. Defaults to
            ``~/.naturo/app_ids/``.
        ttl_seconds: Time-to-live for stored IDs. Defaults to 1800 (30 min).
    """

    def __init__(
        self,
        session: Optional[str] = None,
        storage_root: Optional[Path] = None,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        raw_session = session or os.environ.get(SESSION_ENV_VAR, "").strip()
        self._session = raw_session if raw_session else DEFAULT_SESSION
        self._root = storage_root or DEFAULT_STORAGE_ROOT

        if ttl_seconds is not None:
            self._ttl = ttl_seconds
        else:
            env_ttl = os.environ.get(APP_ID_TTL_ENV_VAR, "").strip()
            self._ttl = int(env_ttl) if env_ttl else APP_ID_TTL_SECONDS

        self._map: Dict[str, AppIdEntry] = {}

    @property
    def _map_path(self) -> Path:
        return self._root / f"{self._session}.json"

    def assign_ids(
        self, windows: Sequence[Any],
    ) -> Dict[str, AppIdEntry]:
        """Assign sequential IDs (a1, a2, ...) to a list of windows.

        Each window object must have ``pid``, ``handle``, ``process_name``,
        and ``title`` attributes (matching :class:`naturo.backends.base.WindowInfo`).

        Args:
            windows: Sequence of window-info objects.

        Returns:
            Mapping of app ID strings to their entries.
        """
        now = time.time()
        self._map = {}

        for i, w in enumerate(windows, start=1):
            app_id = f"a{i}"
            self._map[app_id] = AppIdEntry(
                app_id=app_id,
                pid=w.pid,
                handle=w.handle,
                process_name=w.process_name,
                title=w.title,
                timestamp=now,
            )

        self._persist()
        return dict(self._map)

    def resolve(self, app_id: str) -> Optional[AppIdEntry]:
        """Resolve an app ID to its entry.

        Loads from disk if not already in memory. Returns ``None`` if the
        ID is not found or the map has expired.

        Args:
            app_id: The ID string, e.g. ``"a1"``.

        Returns:
            The entry, or ``None`` if not found / expired.
        """
        if not self._map:
            self._load()

        entry = self._map.get(app_id)
        if entry is None:
            return None

        age = time.time() - entry.timestamp
        if age > self._ttl:
            logger.debug("App ID %s expired (age=%.0fs, ttl=%ds)", app_id, age, self._ttl)
            return None

        return entry

    def list_ids(self) -> Dict[str, AppIdEntry]:
        """Return all current ID mappings (loading from disk if needed).

        Returns:
            Mapping of app ID strings to their entries.
        """
        if not self._map:
            self._load()
        return dict(self._map)

    def _persist(self) -> None:
        """Write the current map to disk atomically."""
        self._root.mkdir(parents=True, exist_ok=True)
        data = {
            aid: asdict(entry) for aid, entry in self._map.items()
        }
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._root), suffix=".tmp",
            )
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, self._map_path)
        except Exception:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

    def _load(self) -> None:
        """Load the map from disk."""
        path = self._map_path
        if not path.exists():
            self._map = {}
            return

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            self._map = {
                aid: AppIdEntry(**entry_data)
                for aid, entry_data in raw.items()
            }
        except (json.JSONDecodeError, TypeError, KeyError) as exc:
            logger.warning("Corrupt app ID map at %s: %s", path, exc)
            self._map = {}


def get_app_id_map(session: Optional[str] = None) -> AppIdMap:
    """Factory: return an AppIdMap for the active session.

    Args:
        session: Override session name. If ``None``, reads from
            ``NATURO_SESSION`` env var.

    Returns:
        Configured :class:`AppIdMap` instance.
    """
    return AppIdMap(session=session)
