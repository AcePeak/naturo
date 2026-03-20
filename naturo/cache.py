"""Element cache — reduce redundant UI tree queries.

Caches element trees per window with a configurable TTL.  Automatically
invalidated after interactions (click, type, etc.) to ensure freshness.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Optional

from naturo.backends.base import ElementInfo

logger = logging.getLogger(__name__)


@dataclass
class _CacheEntry:
    """Internal cache entry with timestamp."""
    tree: ElementInfo
    depth: int
    timestamp: float


class ElementCache:
    """Cache for UI element trees to reduce COM calls on Windows.

    Args:
        ttl: Time-to-live in seconds for cached entries.  Default 2.0s.
    """

    def __init__(self, ttl: float = 2.0) -> None:
        self._ttl = ttl
        self._entries: dict[str, _CacheEntry] = {}
        self._lock = threading.Lock()

    @property
    def ttl(self) -> float:
        """Current TTL setting in seconds."""
        return self._ttl

    @ttl.setter
    def ttl(self, value: float) -> None:
        self._ttl = max(0.0, value)

    def get_tree(self, window_title: str, depth: int) -> Optional[ElementInfo]:
        """Retrieve a cached element tree.

        Args:
            window_title: Window title key.
            depth: Required tree depth. Only returns if cached depth >= requested.

        Returns:
            Cached ElementInfo root, or None if not cached / stale / insufficient depth.
        """
        key = self._make_key(window_title)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if self._is_expired(entry):
                del self._entries[key]
                return None
            if entry.depth < depth:
                return None
            logger.debug("Cache hit for %r (depth=%d)", window_title, depth)
            return entry.tree

    def set_tree(self, window_title: str, depth: int, tree: ElementInfo) -> None:
        """Store an element tree in the cache.

        Args:
            window_title: Window title key.
            depth: Tree depth of the stored tree.
            tree: Root ElementInfo to cache.
        """
        key = self._make_key(window_title)
        with self._lock:
            self._entries[key] = _CacheEntry(
                tree=tree, depth=depth, timestamp=time.monotonic(),
            )
        logger.debug("Cached tree for %r (depth=%d)", window_title, depth)

    def invalidate(self, window_title: str | None = None) -> None:
        """Invalidate cached entries.

        Args:
            window_title: If provided, only invalidate this window's cache.
                If None, invalidate all entries.
        """
        with self._lock:
            if window_title is None:
                count = len(self._entries)
                self._entries.clear()
                logger.debug("Invalidated all %d cache entries", count)
            else:
                key = self._make_key(window_title)
                if key in self._entries:
                    del self._entries[key]
                    logger.debug("Invalidated cache for %r", window_title)

    def is_stale(self, window_title: str) -> bool:
        """Check if the cache entry for a window is stale or missing.

        Args:
            window_title: Window title to check.

        Returns:
            True if no entry exists or the entry has expired.
        """
        key = self._make_key(window_title)
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return True
            return self._is_expired(entry)

    @property
    def size(self) -> int:
        """Number of entries currently in the cache."""
        with self._lock:
            return len(self._entries)

    def clear(self) -> None:
        """Remove all entries (alias for invalidate(None))."""
        self.invalidate(None)

    def _make_key(self, window_title: str) -> str:
        """Normalize window title to cache key."""
        return (window_title or "").strip().lower()

    def _is_expired(self, entry: _CacheEntry) -> bool:
        """Check if an entry has exceeded TTL."""
        return (time.monotonic() - entry.timestamp) > self._ttl
