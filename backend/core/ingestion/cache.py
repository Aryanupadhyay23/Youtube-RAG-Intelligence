import time
import logging
import threading
from typing import Optional, Dict, Any
from collections import OrderedDict

from backend.config import MAX_ACTIVE_VIDEOS, VIDEO_INACTIVITY_TTL_MINUTES
from backend.core.ingestion.vectorstore import delete_video_collection

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
                evicted = False
                for candidate_id in list(self._stores.keys()):
                    if self._ref_counts.get(candidate_id, 0) == 0:
                        self._evict_locked(candidate_id)
                        evicted = True
                        break
                if not evicted:
                    oldest_id = next(iter(self._stores))
                    self._evict_locked(oldest_id)

            self._stores[video_id] = entry
            self._last_accessed[video_id] = time.time()
            self._ref_counts[video_id] = 0
            logger.info(f"Video '{video_id}' stored in ephemeral RAM. (Active count: {len(self._stores)}/{self.max_videos})")

    def acquire(self, video_id: str):
        """Increment in-flight reference count to shield video from eviction during streaming."""
        with self._lock:
            self._ref_counts[video_id] = self._ref_counts.get(video_id, 0) + 1
            self._last_accessed[video_id] = time.time()

    def release(self, video_id: str):
        """Decrement reference count after stream finishes."""
        with self._lock:
            count = self._ref_counts.get(video_id, 1) - 1
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
        try:
            delete_video_collection(video_id)
        except Exception as e:
            logger.warning(f"Error freeing Chroma collection for '{video_id}': {e}")
        logger.info(f"Evicted video '{video_id}' from ephemeral RAM.")
        return True

    def cleanup_expired(self) -> int:
        """Periodic background sweep for inactive videos exceeding TTL."""
        now = time.time()
        evicted_count = 0
        with self._lock:
            for video_id, last_time in list(self._last_accessed.items()):
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
