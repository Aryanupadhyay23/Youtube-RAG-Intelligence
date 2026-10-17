from langchain_core.runnables import RunnableConfig

from backend.core.workflow.state import RAGState
from backend.core.workflow.nodes.helpers import rephrase_query
from backend.core.prompts import CORRECTIVE_PROMPT, CorrectResult


async def correct_query(state: RAGState, config: RunnableConfig) -> dict:
    """Reformulate failed query when retrieved segments lack relevance."""
    return await rephrase_query(
        state,
        CORRECTIVE_PROMPT,
        CorrectResult,
        config["configurable"]["llm"],
        original_query=state["query"],
        failed_query=state.get("rewritten_query", state["query"]),
    )
