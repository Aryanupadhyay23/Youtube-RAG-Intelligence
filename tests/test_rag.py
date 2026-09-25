import unittest
from langchain_core.documents import Document

from core.rrf import reciprocal_rank_fusion
from utils.timestamp import format_timestamp, get_youtube_timestamp_url

class TestRAGComponents(unittest.TestCase):
    
    def test_timestamp_formatting(self):
        self.assertEqual(format_timestamp(65), "01:05")
        self.assertEqual(format_timestamp(3665), "01:01:05")
        
        url = get_youtube_timestamp_url("test_id", 65.5)
        self.assertEqual(url, "https://youtube.com/watch?v=test_id&t=65s")
        
    def test_rrf(self):
        doc1 = Document(page_content="doc1", metadata={"chunk_id": 1})
        doc2 = Document(page_content="doc2", metadata={"chunk_id": 2})
        doc3 = Document(page_content="doc3", metadata={"chunk_id": 3})
        
        # Doc1 is rank 1 in semantic, doc2 rank 2.
        semantic = [(doc1, 0.9), (doc2, 0.8)]
        
        # Doc2 is rank 1 in BM25, doc3 rank 2.
        bm25 = [{"document": doc2, "score": 2.5}, {"document": doc3, "score": 1.5}]
        
        # Doc2 appears in both, should rank high.
        results = reciprocal_rank_fusion(semantic, bm25, k=60, top_n=3)
        
        self.assertEqual(len(results), 3)
        
        # Doc2 has rank 2 in semantic and rank 1 in bm25
        # RRF for Doc1: 1/(60+1) = ~0.01639
        # RRF for Doc2: 1/(60+2) + 1/(60+1) = ~0.01612 + ~0.01639 = ~0.0325
        # RRF for Doc3: 1/(60+2) = ~0.01612
        # So Doc2 should be top.
        
        self.assertEqual(results[0].metadata["chunk_id"], 2)
        self.assertEqual(results[1].metadata["chunk_id"], 1)
        self.assertEqual(results[2].metadata["chunk_id"], 3)

if __name__ == '__main__':
    unittest.main()
