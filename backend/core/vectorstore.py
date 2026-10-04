from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from backend.core.embeddings import load_embeddings
from backend.core.chunking import create_timestamp_aware_chunks


def build_retrievers(video_id: str, transcript_segments: list):
    """
    Builds and returns both Semantic (Chroma) and Sparse (BM25) retrievers.
    """
    documents = create_timestamp_aware_chunks(video_id, transcript_segments)
    if not documents:
        raise ValueError("No valid chunks created from transcript segments.")

    embeddings = load_embeddings()
    vector_store = Chroma.from_documents(documents, embeddings)

    try:
        bm25_retriever = BM25Retriever.from_documents(documents)
    except Exception:
        bm25_retriever = None

    return vector_store, bm25_retriever
