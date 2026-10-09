import os
import gc
import time
import logging
from collections import OrderedDict
from typing import Optional, Dict, Any

from backend.config import MAX_ACTIVE_VIDEOS, VIDEO_INACTIVITY_TTL_MINUTES
from backend.core.vectorstore import delete_video_collection

logger = logging.getLogger(__name__)


class EphemeralVideoStoreCache:
    """
    Pure in-memory ephemeral cache for active video stores with dual eviction:
    1. Capacity-based eviction: caps active videos at MAX_ACTIVE_VIDEOS (LRU).
    2. Inactivity TTL eviction: automatically purges videos idle for > VIDEO_INACTIVITY_TTL_MINUTES.
    - Zero disk footprint (0 MB disk usage).
    - Guarantees RAM is automatically reclaimed even if users close their browsers.
    """

    def __init__(
        self,
        max_active_videos: int = MAX_ACTIVE_VIDEOS,
        ttl_minutes: int = VIDEO_INACTIVITY_TTL_MINUTES,
    ):
        self.max_active_videos = max(1, max_active_videos)
        self.ttl_seconds = max(60, ttl_minutes * 60)
        self._memory_cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._access_times: Dict[str, float] = {}
        self._in_flight: Dict[str, int] = {}

    def acquire(self, video_id: str):
        """Mark video store as actively processing a query to protect it from eviction."""
        self._in_flight[video_id] = self._in_flight.get(video_id, 0) + 1
        self._access_times[video_id] = time.time()

    def release(self, video_id: str):
        """Release active processing lock on a video store."""
        if video_id in self._in_flight:
            self._in_flight[video_id] = max(0, self._in_flight[video_id] - 1)
            if self._in_flight[video_id] == 0:
                del self._in_flight[video_id]

    def get(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve active video store from in-memory cache and refresh access time."""
        # Clean up any expired videos first
        self.cleanup_expired()

        if video_id in self._memory_cache:
            self._memory_cache.move_to_end(video_id)
            self._access_times[video_id] = time.time()
            return self._memory_cache[video_id]
        return None

    def put(self, video_id: str, store_entry: Dict[str, Any]):
        """
        Store video in ephemeral memory.
        If limit is reached, evict the oldest idle Chroma collection.
        """
        # Clean up any expired videos first
        self.cleanup_expired()

        if video_id in self._memory_cache:
            self._memory_cache.move_to_end(video_id)
            self._memory_cache[video_id] = store_entry
            self._access_times[video_id] = time.time()
            return

        # Evict oldest idle video if capacity reached (never evict one with in-flight requests)
        while len(self._memory_cache) >= self.max_active_videos:
            candidate_id = None
            for vid in self._memory_cache:
                if self._in_flight.get(vid, 0) == 0:
                    candidate_id = vid
                    break
            if candidate_id is None:
                # All active videos currently handling requests; allow temporary burst
                break
            del self._memory_cache[candidate_id]
            self._access_times.pop(candidate_id, None)
            logger.info(f"Capacity limit reached. Evicting idle video '{candidate_id}' from RAM.")
            delete_video_collection(candidate_id)

        self._memory_cache[video_id] = store_entry
        self._access_times[video_id] = time.time()
        logger.info(
            f"Stored video '{video_id}' in ephemeral RAM ({len(self._memory_cache)}/{self.max_active_videos} active, "
            f"Inactivity TTL: {self.ttl_seconds // 60}m)."
        )

    def cleanup_expired(self) -> int:
        """Scan and delete all idle video collections that exceeded inactivity TTL."""
        now = time.time()
        expired_ids = [
            vid for vid, last_t in self._access_times.items()
            if (now - last_t) > self.ttl_seconds and self._in_flight.get(vid, 0) == 0
        ]

        for vid in expired_ids:
            idle_mins = int((now - self._access_times.get(vid, now)) // 60)
            logger.info(
                f"Video '{vid}' has been inactive for {idle_mins}m (TTL: {self.ttl_seconds // 60}m). "
                f"Purging Chroma collection and freeing RAM..."
            )
            self._memory_cache.pop(vid, None)
            self._access_times.pop(vid, None)
            delete_video_collection(vid)

        if expired_ids:
            gc.collect()

        return len(expired_ids)

    def evict(self, video_id: str):
        """Manually remove and garbage-collect a specific video."""
        if video_id in self._memory_cache:
            del self._memory_cache[video_id]
            self._access_times.pop(video_id, None)
            delete_video_collection(video_id)
            gc.collect()
            logger.info(f"Explicitly evicted video '{video_id}' from RAM.")

    def clear(self):
        """Wipe all in-memory collections and free RAM."""
        for video_id in list(self._memory_cache.keys()):
            delete_video_collection(video_id)
        self._memory_cache.clear()
        self._access_times.clear()
        gc.collect()
        logger.info("Cleared all ephemeral video stores from RAM.")

    def has(self, video_id: str) -> bool:
        self.cleanup_expired()
        return video_id in self._memory_cache

    def __contains__(self, video_id: str) -> bool:
        return self.has(video_id)
