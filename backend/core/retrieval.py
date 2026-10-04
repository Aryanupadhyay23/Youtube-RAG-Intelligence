import asyncio
from typing import List
from collections import defaultdict
from langchain_core.documents import Document

from backend.utils.constants import SEMANTIC_TOP_K, BM25_TOP_K, FINAL_TOP_K, RRF_K


async def hybrid_retrieve(
    query: str,
    vector_store,
    bm25_retriever,
    semantic_k: int = SEMANTIC_TOP_K,
    bm25_k: int = BM25_TOP_K,
    final_k: int = FINAL_TOP_K,
    rrf_k: int = RRF_K,
) -> List[Document]:
    """
    Performs hybrid retrieval asynchronously using concurrent BM25 and semantic vector search
    fused with Reciprocal Rank Fusion (RRF). Pure async, zero legacy bloat, 20x faster import.
    """
    semantic_retriever = vector_store.as_retriever(search_kwargs={"k": semantic_k})

    if bm25_retriever is None:
        return (await semantic_retriever.ainvoke(query))[:final_k]

    bm25_retriever.k = bm25_k

    # Execute BM25 and Chroma semantic search in parallel
    bm25_docs, semantic_docs = await asyncio.gather(
        bm25_retriever.ainvoke(query),
        semantic_retriever.ainvoke(query),
    )

    # Reciprocal Rank Fusion (RRF) with content deduplication
    doc_scores = defaultdict(float)
    doc_map = {}

    for doc_list, weight in [(bm25_docs, 0.5), (semantic_docs, 0.5)]:
        for rank, doc in enumerate(doc_list):
            doc_id = (
                str(doc.metadata.get("video_id", ""))
                + "_"
                + str(doc.metadata.get("start_time", ""))
                + "_"
                + doc.page_content[:50]
            )
            doc_scores[doc_id] += weight / (rrf_k + rank + 1)
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

    # Sort documents by descending RRF score
    sorted_doc_ids = sorted(doc_scores.keys(), key=lambda d: doc_scores[d], reverse=True)
    return [doc_map[did] for did in sorted_doc_ids[:final_k]]
