import time
import logging
import threading
from typing import Optional, Dict, Any
from collections import OrderedDict
import asyncio

from backend.config import MAX_ACTIVE_VIDEOS, VIDEO_INACTIVITY_TTL_MINUTES

logger = logging.getLogger(__name__)


class EphemeralVideoStoreCache:
    """Thread-safe, 100% In-Memory Video Store Cache with dual eviction."""

    def __init__(
        self,
        max_videos: int = MAX_ACTIVE_VIDEOS,
        ttl_minutes: int = VIDEO_INACTIVITY_TTL_MINUTES,
    ):
        self.max_videos = max(1, max_videos)
        self.ttl_seconds = max(60, ttl_minutes * 60)
        self._stores: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._last_accessed: Dict[str, float] = {}
        self._ref_counts: Dict[str, int] = {}
        self._lock = threading.Lock()
        self._init_lock_guard = threading.Lock()
        self._init_locks: Dict[str, asyncio.Lock] = {}
        self._init_lock_users: Dict[str, int] = {}

    def acquire_init_lock(self, video_id: str) -> asyncio.Lock:
        """Get a shared per-video async lock and register an active waiter/owner."""
        with self._init_lock_guard:
            lock = self._init_locks.get(video_id)
            if lock is None:
                lock = asyncio.Lock()
                self._init_locks[video_id] = lock
            self._init_lock_users[video_id] = self._init_lock_users.get(video_id, 0) + 1
            return lock

    def release_init_lock(self, video_id: str) -> None:
        """Drop a per-video lock after its owner and all waiters have left."""
        with self._init_lock_guard:
            users = self._init_lock_users.get(video_id, 0) - 1
            if users <= 0:
                self._init_lock_users.pop(video_id, None)
                self._init_locks.pop(video_id, None)
            else:
                self._init_lock_users[video_id] = users

    def get(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached store entry, updating LRU and access timestamp."""
        with self._lock:
            if video_id not in self._stores:
                return None
            self._stores.move_to_end(video_id)
            self._last_accessed[video_id] = time.time()
            return self._stores[video_id]

    def get_and_acquire(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached store entry and increment ref count atomically."""
        with self._lock:
            if video_id not in self._stores:
                return None
            self._stores.move_to_end(video_id)
            self._last_accessed[video_id] = time.time()
            self._ref_counts[video_id] = self._ref_counts.get(video_id, 0) + 1
            return self._stores[video_id]

    def put(self, video_id: str, entry: Dict[str, Any]):
        """Put store entry into cache, evicting oldest/idle videos if capacity is exceeded."""
        with self._lock:
            if video_id in self._stores:
                self._stores.move_to_end(video_id)
                self._stores[video_id] = entry
                self._last_accessed[video_id] = time.time()
                return

            while len(self._stores) >= self.max_videos:
                evictable_id = None
                for candidate_id in list(self._stores.keys()):
                    if self._ref_counts.get(candidate_id, 0) == 0:
                        evictable_id = candidate_id
                        break
                if evictable_id is not None:
                    self._evict_locked(evictable_id)
                else:
                    # Every cached video is shielded by an active stream. Never evict
                    # a live vector store out from under a stream; allow temporary
                    # over-capacity instead.
                    logger.warning(
                        f"All {len(self._stores)} cached videos are in active use; "
                        f"allowing temporary over-capacity for '{video_id}'."
                    )
                    break

            self._stores[video_id] = entry
            self._last_accessed[video_id] = time.time()
            self._ref_counts[video_id] = 0
            logger.info(
                f"Video '{video_id}' stored in ephemeral RAM. (Active count: {len(self._stores)}/{self.max_videos})"
            )

    def release(self, video_id: str):
        """Decrement reference count after stream finishes.

        No-ops for videos no longer present in the cache so that releases for
        evicted ids do not create ghost bookkeeping entries.
        """
        with self._lock:
            if video_id not in self._stores:
                self._ref_counts.pop(video_id, None)
                self._last_accessed.pop(video_id, None)
                return
            count = self._ref_counts.get(video_id, 0) - 1
            self._ref_counts[video_id] = max(0, count)
            self._last_accessed[video_id] = time.time()

    def evict(self, video_id: str) -> bool:
        """Manually evict a video vector store to immediately reclaim RAM."""
        with self._lock:
            return self._evict_locked(video_id)

    def _evict_locked(self, video_id: str) -> bool:
        if video_id not in self._stores:
            return False
        self._stores.pop(video_id, None)
        self._last_accessed.pop(video_id, None)
        self._ref_counts.pop(video_id, None)
        logger.info(f"Evicted video '{video_id}' from ephemeral RAM.")
        return True

    def cleanup_expired(self) -> int:
        """Periodic background sweep for inactive videos exceeding TTL."""
        now = time.time()
        evicted_count = 0
        with self._lock:
            for video_id, last_time in list(self._last_accessed.items()):
                if video_id not in self._stores:
                    # Ghost bookkeeping entry left behind by an evicted video.
                    if now - last_time > self.ttl_seconds:
                        self._last_accessed.pop(video_id, None)
                        self._ref_counts.pop(video_id, None)
                    continue
                if self._ref_counts.get(video_id, 0) > 0:
                    continue
                if now - last_time > self.ttl_seconds:
                    if self._evict_locked(video_id):
                        evicted_count += 1
        return evicted_count

    def clear(self):
        """Full purge on server shutdown."""
        with self._lock:
            for video_id in list(self._stores.keys()):
                self._evict_locked(video_id)
