from langchain_community.vectorstores import Chroma
from core.embeddings import load_embeddings
from core.chunking import create_timestamp_aware_chunks
from core.bm25 import BM25Retriever

def build_retrievers(video_id: str, transcript_segments: list):
    """
    Builds and returns both Semantic (FAISS) and Sparse (BM25) retrievers.
    """
    # 1. Create timestamp-aware chunks
    documents = create_timestamp_aware_chunks(video_id, transcript_segments)
    
    if not documents:
        raise ValueError("No valid chunks created from transcript segments.")

    # 2. Build Semantic Store (Chroma)
    embeddings = load_embeddings()
    vector_store = Chroma.from_documents(documents, embeddings)
    
    # 3. Build Sparse Retriever (BM25)
    try:
        bm25_retriever = BM25Retriever(documents)
    except ImportError:
        bm25_retriever = None
        
    return vector_store, bm25_retriever