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
        class FakeQdrantCache:
            enabled = True

            def __init__(self):
                self.store_calls = 0

            def load_video(self, _video_id):
                return None

            def store_video(self, _video_id, _documents, _metadata, _text, _segments):
                self.store_calls += 1
                time.sleep(0.03)
                return object()

        cache = EphemeralVideoStoreCache()
        qdrant = FakeQdrantCache()
        request = SimpleNamespace(
            app=SimpleNamespace(state=SimpleNamespace(video_stores=cache, qdrant_video_cache=qdrant))
        )
        counts = {"transcript": 0, "chunks": 0}

        def fetch_transcript(_video_id):
            counts["transcript"] += 1
            time.sleep(0.03)
            return "Transcript text", [{"text": "Transcript text", "start": 0, "duration": 1}]

        def create_chunks(_video_id, _segments):
            counts["chunks"] += 1
            time.sleep(0.03)
            return [object()]

        with (
            patch("backend.routes.video.routes.fetch_transcript", side_effect=fetch_transcript),
            patch("backend.routes.video.routes.get_video_metadata", return_value={"title": "Test"}),
            patch("backend.routes.video.routes.create_timestamp_aware_chunks", side_effect=create_chunks),
            patch("backend.routes.video.routes.build_bm25_retriever", return_value=object()),
        ):
            results = await asyncio.gather(
                init_video(InitRequest(video_id=VIDEO_ID), request),
                init_video(InitRequest(video_id=VIDEO_ID), request),
            )

        self.assertEqual(counts, {"transcript": 1, "chunks": 1})
        self.assertEqual(qdrant.store_calls, 1)
        self.assertEqual({result["status"] for result in results}, {"success", "already initialized"})
        self.assertEqual(len(cache._init_locks), 0)

    async def test_qdrant_hit_skips_transcript_and_embedding_creation(self):
        class FakeQdrantCache:
            enabled = True

            def load_video(self, _video_id):
                return {
                    "documents": [object()],
                    "metadata": {"title": "Persisted"},
                    "transcript_text": "Already indexed transcript",
                    "transcript_segments": [{"text": "Already indexed transcript", "start": 0, "duration": 1}],
                }

            def vector_store_for(self, _video_id):
                return object()

        cache = EphemeralVideoStoreCache()
        state = SimpleNamespace(video_stores=cache, qdrant_video_cache=FakeQdrantCache())
        request = SimpleNamespace(app=SimpleNamespace(state=state))

        with (
            patch("backend.routes.video.routes.fetch_transcript") as fetch_transcript,
            patch("backend.routes.video.routes.get_video_metadata") as get_video_metadata,
            patch("backend.routes.video.routes.build_bm25_retriever", return_value=object()),
        ):
            result = await init_video(InitRequest(video_id=VIDEO_ID), request)

        self.assertEqual(result["status"], "restored from qdrant")
        self.assertEqual(result["metadata"], {"title": "Persisted"})
        fetch_transcript.assert_not_called()
        get_video_metadata.assert_not_called()
