import logging
from langchain_core.messages import HumanMessage, AIMessage

from backend.core.workflow.state import RAGState
from backend.utils.constants import MEMORY_WINDOW
from backend.utils.timestamp import get_youtube_timestamp_url, format_time

logger = logging.getLogger(__name__)


def format_docs_with_timestamps(docs) -> str:
    """Format retrieved documents with human-readable timestamps and source links."""
    formatted = []
    for d in docs:
        start_sec = d.metadata.get("start_time", 0)
        end_sec = d.metadata.get("end_time", 0)
        start_str = format_time(start_sec)
        end_str = format_time(end_sec)
        vid_id = d.metadata.get("video_id", "")
        url = get_youtube_timestamp_url(vid_id, start_sec) if vid_id else ""
        formatted.append(
            f"Timestamp: [{start_str} - {end_str}] (Link: {url})\nContent: {d.page_content}"
        )
    return "\n\n".join(formatted)


def format_chat_history(history: list) -> list:
    """Convert the last MEMORY_WINDOW turns to LangChain Human/AI messages."""
    messages = []
    for turn in history[-MEMORY_WINDOW:]:
        messages.extend([
            HumanMessage(content=turn["user"]),
            AIMessage(content=turn["ai"]),
        ])
    return messages


async def rephrase_query(state: RAGState, prompt, output_schema, llm, **kwargs) -> dict:
    """Generic query rewriting logic with structured output fallback."""
    query = state.get("rewritten_query", state["query"])
    messages = prompt.format_messages(
        chat_history=format_chat_history(state.get("chat_history", [])),
        **kwargs
    )

    try:
        response = await llm.with_structured_output(output_schema, method="function_calling").ainvoke(messages)
        new_query = getattr(response, "standalone_query", getattr(response, "corrected_query", query))
        if hasattr(response, "needs_rewrite") and not response.needs_rewrite:
            new_query = query
    except Exception as e:
        logger.warning(f"Structured output error in rephrase_query: {e}. Fallback to query.")
        new_query = query

    logger.info(f"Query updated: '{query}' -> '{new_query}'")
    return {"rewritten_query": new_query}
