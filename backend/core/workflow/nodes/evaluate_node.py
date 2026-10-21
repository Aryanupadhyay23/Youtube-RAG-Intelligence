import logging
from langchain_core.runnables import RunnableConfig

from backend.core.workflow.state import RAGState
from backend.core.prompts import GRADER_PROMPT, GradeResult
from backend.utils.constants import MAX_RETRIEVAL_ATTEMPTS

logger = logging.getLogger(__name__)


async def evaluate_retrieval(state: RAGState, config: RunnableConfig) -> dict:
    """Grade retrieved document relevance to decide between answer generation or corrective action."""
    docs = state.get("retrieved_documents", [])
    if not docs:
        return {"retrieval_score": "POOR"}

    query = state.get("rewritten_query", state["query"])
    # Grade against top 3 chunks combined so an introductory first chunk doesn't falsely cause POOR grading
    combined_content = "\n\n---\n\n".join(d.page_content for d in docs[:3])
    messages = GRADER_PROMPT.format_messages(question=query, document=combined_content)
    try:
        response = await config["configurable"]["llm"].with_structured_output(
            GradeResult, method="function_calling"
        ).ainvoke(messages)
        is_rel = bool(getattr(response, "relevant", False))
        score = getattr(response, "score", None)
        if score is not None and score == 0:
            is_rel = False
        grade = "GOOD" if is_rel else "POOR"
    except Exception as e:
        err_msg = str(e).lower()
        if "not relevant" in err_msg or "irrelevant" in err_msg or "score: 0" in err_msg:
            grade = "POOR"
        else:
            logger.warning(f"Grading failed with unexpected error, defaulting to GOOD: {e}")
            grade = "GOOD"

    logger.info(f"Retrieval graded as: {grade}")
    return {"retrieval_score": grade}


def route_after_evaluation(state: RAGState) -> str:
    """Conditional edge router following retrieval evaluation."""
    if state["retrieval_score"] == "GOOD":
        return "generate_answer"
    return "correct_query" if state["retrieval_attempt"] < MAX_RETRIEVAL_ATTEMPTS else "web_search"
