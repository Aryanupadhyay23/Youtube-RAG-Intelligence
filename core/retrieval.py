from typing import List
from langchain_core.documents import Document

from core.rrf import reciprocal_rank_fusion
from utils.constants import SEMANTIC_TOP_K, BM25_TOP_K, FINAL_TOP_K, RRF_K

def hybrid_retrieve(
    query: str,
    vector_store,
    bm25_retriever,
    semantic_k: int = SEMANTIC_TOP_K,
    bm25_k: int = BM25_TOP_K,
    final_k: int = FINAL_TOP_K,
    rrf_k: int = RRF_K
) -> List[Document]:
    """
    Performs hybrid retrieval using both Semantic Search (Chroma) and Keyword Search (BM25).
    Combines results using Reciprocal Rank Fusion (RRF).
    """
    # 1. Semantic Retrieval
    # vector_store.similarity_search_with_score returns List[Tuple[Document, float]]
    semantic_results = vector_store.similarity_search_with_score(query, k=semantic_k)
    
    # 2. Keyword Retrieval (BM25)
    bm25_results = bm25_retriever.retrieve(query, k=bm25_k)
    
    # 3. Combine with RRF
    fused_documents = reciprocal_rank_fusion(
        semantic_results=semantic_results,
        bm25_results=bm25_results,
        k=rrf_k,
        top_n=final_k
    )
    
    return fused_documents
