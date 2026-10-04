import re
import gc
import logging
import chromadb
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from backend.core.embeddings import load_embeddings
from backend.core.chunking import create_timestamp_aware_chunks

logger = logging.getLogger(__name__)

# Single in-memory ephemeral client (0 MB disk footprint)
_ephemeral_client = chromadb.EphemeralClient()


def _sanitize_collection_name(video_id: str) -> str:
    """Chroma collection names must be 3-63 characters and match [a-zA-Z0-9_-]."""
    clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", video_id)
    return f"yt_{clean_id}"[:63]


def delete_video_collection(video_id: str):
    """Cleanly delete the in-memory Chroma collection and trigger garbage collection."""
    col_name = _sanitize_collection_name(video_id)
    try:
        _ephemeral_client.delete_collection(col_name)
        logger.info(f"Deleted in-memory collection '{col_name}' for video {video_id}.")
    except Exception as e:
        logger.debug(f"Collection '{col_name}' could not be deleted (might not exist): {e}")
    gc.collect()


def build_retrievers(video_id: str, transcript_segments: list):
    """
    Builds 100% in-memory Semantic (Chroma Ephemeral) and Sparse (BM25) retrievers.
    Leaves 0 MB footprint on disk.
    """
    documents = create_timestamp_aware_chunks(video_id, transcript_segments)
    if not documents:
        raise ValueError("No valid chunks created from transcript segments.")

    embeddings = load_embeddings()
    col_name = _sanitize_collection_name(video_id)

    # Clean existing collection with the same name if present
    delete_video_collection(video_id)

    logger.info(f"Creating in-memory Chroma collection '{col_name}' for video {video_id} (Ephemeral RAM only)...")
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        client=_ephemeral_client,
        collection_name=col_name,
    )

    try:
        bm25_retriever = BM25Retriever.from_documents(documents)
    except Exception as e:
        logger.warning(f"BM25 initialization failed: {e}")
        bm25_retriever = None

    return vector_store, bm25_retriever
