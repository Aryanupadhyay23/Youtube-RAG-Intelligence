"""Local BM25 keyword index used alongside Qdrant semantic search."""

import re

from langchain_community.retrievers import BM25Retriever

from backend.utils.constants import BM25_TOP_K


def _bm25_tokenize(text: str) -> list[str]:
    """Split text into lowercase words for keyword matching."""
    return re.findall(r"\w+", text.lower())


def build_bm25_retriever(documents) -> BM25Retriever:
    """Build the keyword half of hybrid retrieval from a video's chunks."""
    return BM25Retriever.from_documents(
        documents,
        k=BM25_TOP_K,
        preprocess_func=_bm25_tokenize,
    )
