from langgraph.graph import StateGraph, END

from backend.core.workflow.state import RAGState
from backend.core.workflow.nodes import (
    rewrite_query,
    hybrid_retrieve_node,
    evaluate_retrieval,
    route_after_evaluation,
    correct_query,
    web_search,
    generate_answer,
)


def build_langgraph(checkpointer=None):
    """Build and compile the LangGraph CRAG workflow connecting modular nodes."""
    workflow = StateGraph(RAGState)

    # Register modular nodes
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("hybrid_retrieve", hybrid_retrieve_node)
    workflow.add_node("evaluate_retrieval", evaluate_retrieval)
    workflow.add_node("correct_query", correct_query)
    workflow.add_node("web_search", web_search)
    workflow.add_node("generate_answer", generate_answer)

    # Connect edges
    workflow.set_entry_point("rewrite_query")
    workflow.add_edge("rewrite_query", "hybrid_retrieve")
    workflow.add_edge("hybrid_retrieve", "evaluate_retrieval")
    workflow.add_conditional_edges("evaluate_retrieval", route_after_evaluation)
    workflow.add_edge("correct_query", "hybrid_retrieve")
    workflow.add_edge("web_search", "generate_answer")
    workflow.add_edge("generate_answer", END)

    return workflow.compile(checkpointer=checkpointer)
