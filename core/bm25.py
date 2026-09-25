import re
from typing import List, Dict
from langchain_core.documents import Document

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

class BM25Retriever:
    def __init__(self, documents: List[Document]):
        self.documents = documents
        if BM25Okapi is None:
            raise ImportError("Please install rank_bm25 to use BM25Retriever.")
        
        # Tokenize corpus
        corpus = [self._tokenize(doc.page_content) for doc in documents]
        self.bm25 = BM25Okapi(corpus)

    def _tokenize(self, text: str) -> List[str]:
        # Simple tokenization by word, converting to lowercase and stripping punctuation
        return re.findall(r'\b\w+\b', text.lower())

    def retrieve(self, query: str, k: int = 20) -> List[Dict]:
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Sort indices by score in descending order
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append({
                    "document": self.documents[idx],
                    "score": scores[idx]
                })
        return results
