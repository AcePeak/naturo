"""Per-PID detection result cache with TTL.

Caches framework detection results to avoid re-probing the same process
on every command invocation. Cache is invalidated when:
- TTL expires (default 300 seconds / 5 minutes)
- Process has restarted (different creation time)
- Manual invalidation via clear()
"""

import time
from dataclasses import dataclass
from typing import Dict, Optional

from naturo.detect.models import DetectionResult


# Default cache TTL in seconds
DEFAULT_TTL_SECONDS = 300


@dataclass
class CacheEntry:
    """A cached detection result with metadata.

    Attributes:
        result: The cached DetectionResult.
        timestamp: When this entry was created (monotonic time).
        process_create_time: Process creation time for staleness detection.
    """

    result: DetectionResult
    timestamp: float
    process_create_time: Optional[float] = None


class DetectionCache:
    """Thread-safe per-PID detection result cache.

    Attributes:
        ttl_seconds: How long entries remain valid.
    """

    def __init__(self, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        """Initialize the cache.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds.
        """
        self._entries: Dict[int, CacheEntry] = {}
        self.ttl_seconds = ttl_seconds

    def get(self, pid: int, process_create_time: Optional[float] = None) -> Optional[DetectionResult]:
        """Retrieve a cached detection result for a PID.

        Args:
            pid: Process ID to look up.
            process_create_time: If provided, validates that the cached entry
                matches this creation time (detects process restarts).

        Returns:
            The cached DetectionResult, or None if not found/expired/stale.
        """
        entry = self._entries.get(pid)
        if entry is None:
            return None

        # Check TTL
        age = time.monotonic() - entry.timestamp
        if age > self.ttl_seconds:
            del self._entries[pid]
            return None

        # Check process restart (if creation time provided)
        if (process_create_time is not None
                and entry.process_create_time is not None
                and entry.process_create_time != process_create_time):
            del self._entries[pid]
            return None

        return entry.result

    def put(self, pid: int, result: DetectionResult,
            process_create_time: Optional[float] = None) -> None:
        """Store a detection result in the cache.

        Args:
            pid: Process ID.
            result: Detection result to cache.
            process_create_time: Process creation time for staleness detection.
        """
        self._entries[pid] = CacheEntry(
            result=result,
            timestamp=time.monotonic(),
            process_create_time=process_create_time,
        )

    def invalidate(self, pid: int) -> bool:
        """Remove a specific PID from the cache.

        Args:
            pid: Process ID to remove.

        Returns:
            True if the entry existed and was removed.
        """
        return self._entries.pop(pid, None) is not None

    def clear(self) -> None:
        """Remove all cached entries."""
        self._entries.clear()

    def size(self) -> int:
        """Return the number of cached entries."""
        return len(self._entries)

    def cleanup_expired(self) -> int:
        """Remove all expired entries.

        Returns:
            Number of entries removed.
        """
        now = time.monotonic()
        expired = [
            pid for pid, entry in self._entries.items()
            if (now - entry.timestamp) > self.ttl_seconds
        ]
        for pid in expired:
            del self._entries[pid]
        return len(expired)


# Module-level singleton cache
_global_cache = DetectionCache()


def get_cache() -> DetectionCache:
    """Return the global detection cache singleton.

    Returns:
        The global DetectionCache instance.
    """
    return _global_cache
