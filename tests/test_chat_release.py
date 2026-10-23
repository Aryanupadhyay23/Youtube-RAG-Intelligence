import unittest
from types import SimpleNamespace
from unittest.mock import patch

from backend.core.ingestion.cache import EphemeralVideoStoreCache
from backend.routes.chat.routes import chat_stream
from backend.routes.chat.schemas import ChatRequest

VIDEO_ID = "dQw4w9WgXcQ"


class FakeCheckpointer:
    def get_tuple(self, config):
        return None


class FakeGraph:
    async def astream_events(self, inputs, config=None, version="v1"):
        if False:
            yield {}


def make_request(cache):
    state = SimpleNamespace(
        video_stores=cache,
        checkpointer=FakeCheckpointer(),
        rag_graph=FakeGraph(),
    )
    return SimpleNamespace(app=SimpleNamespace(state=state))


def make_cache():
    cache = EphemeralVideoStoreCache()
    cache.put(VIDEO_ID, {"vector_store": object(), "bm25_retriever": object()})
    return cache


class TestChatCacheRelease(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cache = make_cache()
        self.request = ChatRequest(
            video_id=VIDEO_ID,
            chat_id="chat-1",
            query="What is RAG?",
            chat_history=[{"user": "hi", "ai": "hello"}],
        )

    async def start_stream(self):
        with patch("backend.routes.chat.routes.load_llm", return_value=object()):
            return await chat_stream(self.request, make_request(self.cache))

    async def test_release_runs_when_generator_is_never_iterated(self):
        response = await self.start_stream()
        self.assertEqual(self.cache._ref_counts[VIDEO_ID], 1)

        await response.background()

        self.assertEqual(self.cache._ref_counts[VIDEO_ID], 0)

    async def test_release_is_idempotent(self):
        response = await self.start_stream()
        async for _ in response.body_iterator:
            pass

        self.assertEqual(self.cache._ref_counts[VIDEO_ID], 0)

        await response.background()

        self.assertEqual(self.cache._ref_counts[VIDEO_ID], 0)
