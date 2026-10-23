from typing import TypedDict, List


class RAGState(TypedDict):
    """LangGraph CRAG Agent State schema across conversation turns."""

    query: str
    rewritten_query: str
    chat_history: List[dict]
    retrieved_documents: list
    retrieval_score: str
    retrieval_attempt: int
    context: str
    answer: str
    video_id: str
