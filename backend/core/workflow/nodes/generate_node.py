from langchain_core.runnables import RunnableConfig

from backend.core.workflow.state import RAGState
from backend.core.workflow.nodes.helpers import format_docs_with_timestamps, format_chat_history
from backend.core.prompts import ANSWER_PROMPT
from backend.utils.constants import MEMORY_WINDOW


async def generate_answer(state: RAGState, config: RunnableConfig) -> dict:
    """Generate final grounded answer with timestamps and manage checkpointer state."""
    context = state.get("context", "")
    if not context and state.get("retrieved_documents"):
        context = format_docs_with_timestamps(state["retrieved_documents"])

    # Pass original user query to prompt so LLM responds in the user's native language & tone
    messages = ANSWER_PROMPT.format_messages(
        context=context,
        chat_history=format_chat_history(state.get("chat_history", [])),
        query=state["query"],
    )

    response = await config["configurable"]["llm"].ainvoke(messages, config)
    answer = response.content
    if isinstance(answer, list):
        answer = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in answer)

    # Maintain conversational memory in agent state across turns via LangGraph Checkpointer
    updated_history = list(state.get("chat_history") or [])
    updated_history.append({"user": state["query"], "ai": answer})
    if len(updated_history) > MEMORY_WINDOW:
        updated_history = updated_history[-MEMORY_WINDOW:]

    return {"answer": answer, "context": context, "chat_history": updated_history}
