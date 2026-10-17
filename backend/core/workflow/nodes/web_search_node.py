import logging

from backend.core.workflow.state import RAGState
from backend.core.workflow.nodes.helpers import format_docs_with_timestamps
from backend.services.search import fallback_web_search

logger = logging.getLogger(__name__)


async def web_search(state: RAGState) -> dict:
    """Fallback web search when video retrieval attempts are exhausted."""
    query = state.get("rewritten_query", state["query"])
    results = await fallback_web_search(query)
    logger.info("Web search used as supplementary/fallback context.")
    transcript_part = ""
    if state.get("retrieved_documents"):
        transcript_part = f"[VIDEO TRANSCRIPT CONTEXT]\n{format_docs_with_timestamps(state['retrieved_documents'])}\n\n"
    return {"context": f"{transcript_part}[WEB SEARCH RESULTS]\n{results}"}
