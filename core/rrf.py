from typing import List, Dict, Tuple
from langchain_core.documents import Document

def reciprocal_rank_fusion(
    semantic_results: List[Tuple[Document, float]], 
    bm25_results: List[Dict], 
    k: int = 60, 
    top_n: int = 5
) -> List[Document]:
    """
    Combines semantic and BM25 results using Reciprocal Rank Fusion (RRF).
    semantic_results: list of (Document, score) from FAISS
    bm25_results: list of {"document": Document, "score": float} from BM25
    """
    
    rrf_scores = {}
    
    # helper to process results
    def add_to_rrf(results_list, is_semantic=False):
        for rank, item in enumerate(results_list):
            if is_semantic:
                doc, _ = item
            else:
                doc = item["document"]
            
            # Use chunk_id as unique identifier for documents
            doc_id = doc.metadata.get("chunk_id", hash(doc.page_content))
            
            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = {"doc": doc, "score": 0.0}
            
            # RRF formula: 1 / (k + rank)
            # rank is 0-indexed, so we add 1 for the formula
            rrf_scores[doc_id]["score"] += 1.0 / (k + rank + 1)
            
    add_to_rrf(semantic_results, is_semantic=True)
    add_to_rrf(bm25_results, is_semantic=False)
    
    # Sort by RRF score descending
    sorted_docs = sorted(rrf_scores.values(), key=lambda x: x["score"], reverse=True)
    
    # Return top N documents
    return [item["doc"] for item in sorted_docs[:top_n]]
