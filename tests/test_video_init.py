import asyncio
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.core.ingestion.cache import EphemeralVideoStoreCache
from backend.routes.video.routes import init_video
from backend.routes.video.schemas import InitRequest


VIDEO_ID = "dQw4w9WgXcQ"


class TestVideoInitializationConcurrency(unittest.IsolatedAsyncioTestCase):
    async def test_same_video_is_built_once_for_concurrent_init_requests(self):
        cache = EphemeralVideoStoreCache()
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(video_stores=cache)))
        counts = {"transcript": 0, "build": 0}

        def fetch_transcript(_video_id):
            counts["transcript"] += 1
            time.sleep(0.03)
            return "Transcript text", [{"text": "Transcript text", "start": 0, "duration": 1}]

        def build_retrievers(_video_id, _segments):
            counts["build"] += 1
            time.sleep(0.03)
            return object(), object()

        with (
            patch("backend.routes.video.routes.fetch_transcript", side_effect=fetch_transcript),
            patch("backend.routes.video.routes.get_video_metadata", return_value={"title": "Test"}),
            patch("backend.routes.video.routes.build_retrievers", side_effect=build_retrievers),
        ):
            results = await asyncio.gather(
                init_video(InitRequest(video_id=VIDEO_ID), request),
                init_video(InitRequest(video_id=VIDEO_ID), request),
            )

        self.assertEqual(counts, {"transcript": 1, "build": 1})
        self.assertEqual({result["status"] for result in results}, {"success", "already initialized"})
        self.assertEqual(len(cache._init_locks), 0)
