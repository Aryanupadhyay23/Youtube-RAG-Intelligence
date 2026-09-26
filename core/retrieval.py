from typing import List
from langchain_core.documents import Document
from langchain_classic.retrievers import EnsembleRetriever
import asyncio

from utils.constants import SEMANTIC_TOP_K, BM25_TOP_K, FINAL_TOP_K, RRF_K

async def hybrid_retrieve(
    query: str,
    vector_store,
    bm25_retriever,
    semantic_k: int = SEMANTIC_TOP_K,
    bm25_k: int = BM25_TOP_K,
    final_k: int = FINAL_TOP_K,
    rrf_k: int = RRF_K
) -> List[Document]:
    """
    Performs hybrid retrieval asynchronously using Langchain's EnsembleRetriever.
    """
    # 1. Prepare retrievers
    semantic_retriever = vector_store.as_retriever(search_kwargs={"k": semantic_k})
    bm25_retriever.k = bm25_k
    
    # 2. Build Ensemble Retriever
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, semantic_retriever],
        weights=[0.5, 0.5],
        c=rrf_k
    )
    
    # 3. Retrieve and fuse
    fused_documents = await ensemble_retriever.ainvoke(query)
    
    return fused_documents[:final_k]
