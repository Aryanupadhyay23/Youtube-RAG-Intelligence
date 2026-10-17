from langchain_core.runnables import RunnableConfig

from backend.core.workflow.state import RAGState
from backend.core.workflow.nodes.helpers import rephrase_query
from backend.core.prompts import REWRITE_PROMPT, RewriteResult


async def rewrite_query(state: RAGState, config: RunnableConfig) -> dict:
    """Rewrite conversational follow-up questions into standalone queries."""
    if not state.get("chat_history"):
        return {"rewritten_query": state["query"]}
    return await rephrase_query(
        state, REWRITE_PROMPT, RewriteResult, config["configurable"]["llm"], question=state["query"]
    )
