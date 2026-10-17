import unittest
import asyncio
from langchain_core.documents import Document
from backend.core.ingestion import hybrid_retrieve


class _FakeRetriever:
    def __init__(self, docs):
        self._docs = docs

    async def ainvoke(self, query):
        return self._docs


class _FakeVectorStore:
    def __init__(self, docs):
        self._docs = docs

    def as_retriever(self, search_kwargs=None):
        return _FakeRetriever(self._docs)


class TestRetrieval(unittest.TestCase):
    def test_hybrid_retrieval_merges_and_deduplicates(self):
        d1 = Document(page_content="Apple banana", metadata={"video_id": "v1", "start_time": 0})
        d2 = Document(page_content="Cherry date", metadata={"video_id": "v1", "start_time": 10})
        bm25 = _FakeRetriever([d1])
        vector = _FakeVectorStore([d1, d2])

        loop = asyncio.new_event_loop()
        try:
            results = loop.run_until_complete(
                hybrid_retrieve("test", vector, bm25, final_k=5)
            )
            self.assertEqual(len(results), 2)
            self.assertEqual(results[0].page_content, "Apple banana")
        finally:
            loop.close()
