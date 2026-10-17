import logging
from langchain_core.runnables import RunnableConfig

from backend.core.workflow.state import RAGState
from backend.core.ingestion import hybrid_retrieve

logger = logging.getLogger(__name__)


async def hybrid_retrieve_node(state: RAGState, config: RunnableConfig) -> dict:
    """Execute hybrid dense + sparse retrieval (ChromaDB + BM25 with RRF)."""
    query = state.get("rewritten_query", state["query"])
    vector_store = config["configurable"]["vector_store"]
    bm25 = config["configurable"]["bm25_retriever"]
    attempt = state.get("retrieval_attempt", 0) + 1

    docs = await hybrid_retrieve(query, vector_store, bm25)
    logger.info(f"Retrieval attempt {attempt}: found {len(docs)} documents.")
    return {"retrieved_documents": docs, "retrieval_attempt": attempt}
