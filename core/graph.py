import logging
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from core.retrieval import hybrid_retrieve
from core.prompts import (
    SYSTEM_PROMPT, 
    REWRITE_PROMPT, 
    GRADER_PROMPT,
    WEB_SEARCH_ROUTER_PROMPT
)
from services.web_search_service import fallback_web_search
from utils.constants import MAX_RETRIEVAL_ATTEMPTS
from utils.timestamp import get_youtube_timestamp_url

logger = logging.getLogger(__name__)

class RAGState(TypedDict):
    query: str
    rewritten_query: str
    chat_history: List[dict]
    retrieved_documents: list
    retrieval_score: str
    retrieval_attempt: int
    context: str
    answer: str
    video_id: str
    vector_store: any
    bm25_retriever: any
    llm: any

def format_docs_with_timestamps(docs):
    formatted = []
    for doc in docs:
        video_id = doc.metadata.get("video_id")
        start = doc.metadata.get("start_time", 0)
        
        url = get_youtube_timestamp_url(video_id, start) if video_id else ""
        
        formatted.append(f"Content: {doc.page_content}\nSource: {url}")
    return "\n\n".join(formatted)

def rewrite_query(state: RAGState) -> RAGState:
    query = state["query"]
    history = state.get("chat_history", [])
    llm = state["llm"]
    
    if not history:
        return {"rewritten_query": query}
        
    formatted_history = "\n".join([f"User: {h['user']}\nAI: {h['ai']}" for h in history])
    
    prompt = REWRITE_PROMPT.format(chat_history=formatted_history, question=query)
    response = llm.invoke([HumanMessage(content=prompt)])
    
    rewritten = response.content.strip()
    logger.info(f"Query rewritten: '{query}' -> '{rewritten}'")
    return {"rewritten_query": rewritten}

def hybrid_retrieve_node(state: RAGState) -> RAGState:
    query = state.get("rewritten_query", state["query"])
    vector_store = state["vector_store"]
    bm25 = state["bm25_retriever"]
    attempt = state.get("retrieval_attempt", 0) + 1
    
    docs = hybrid_retrieve(query, vector_store, bm25)
    
    logger.info(f"Retrieval attempt {attempt}: found {len(docs)} documents.")
    return {"retrieved_documents": docs, "retrieval_attempt": attempt}

def evaluate_retrieval(state: RAGState) -> RAGState:
    docs = state["retrieved_documents"]
    query = state.get("rewritten_query", state["query"])
    llm = state["llm"]
    
    if not docs:
        return {"retrieval_score": "POOR"}
        
    # Grade top document
    top_doc = docs[0].page_content
    prompt = GRADER_PROMPT.format(question=query, document=top_doc)
    
    response = llm.invoke([HumanMessage(content=prompt)])
    score = response.content.strip().lower()
    
    grade = "GOOD" if "yes" in score else "POOR"
    logger.info(f"Retrieval graded as: {grade}")
    return {"retrieval_score": grade}

def correct_query(state: RAGState) -> RAGState:
    query = state.get("rewritten_query", state["query"])
    llm = state["llm"]
    
    # Simple correction prompt
    prompt = f"The query '{query}' did not return relevant results. Rewrite it to be broader or use different keywords to improve search."
    response = llm.invoke([HumanMessage(content=prompt)])
    
    corrected = response.content.strip()
    logger.info(f"Query corrected: '{query}' -> '{corrected}'")
    return {"rewritten_query": corrected}

def web_search(state: RAGState) -> RAGState:
    query = state.get("rewritten_query", state["query"])
    results = fallback_web_search(query)
    logger.info("Web search used as fallback.")
    return {"context": f"[WEB SEARCH RESULTS]\n{results}"}

def generate_answer(state: RAGState) -> RAGState:
    # If context is not already populated (e.g. by web search), format docs
    if not state.get("context") and state.get("retrieved_documents"):
        state["context"] = format_docs_with_timestamps(state["retrieved_documents"])
        
    context = state.get("context", "")
    query = state.get("rewritten_query", state["query"])
    history = state.get("chat_history", [])
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)}
    ]
    
    for h in history:
        messages.append({"role": "user", "content": h["user"]})
        messages.append({"role": "assistant", "content": h["ai"]})
        
    messages.append({"role": "user", "content": query})
    
    # We will pass messages to LLM in the main app to support streaming,
    # or we can do it here. To preserve streaming natively in Streamlit, 
    # we might want to return the prompt configuration and stream outside, 
    # but LangGraph supports streaming events. Let's just generate it here 
    # and the app will stream using langgraph event streaming.
    return {"answer": messages} # Returning messages payload for streaming

def route_after_evaluation(state: RAGState):
    score = state["retrieval_score"]
    attempt = state["retrieval_attempt"]
    
    if score == "GOOD":
        return "generate_answer"
    else:
        if attempt < MAX_RETRIEVAL_ATTEMPTS:
            return "correct_query"
        else:
            return "web_search"

def build_langgraph(checkpointer=None):
    workflow = StateGraph(RAGState)
    
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("hybrid_retrieve", hybrid_retrieve_node)
    workflow.add_node("evaluate_retrieval", evaluate_retrieval)
    workflow.add_node("correct_query", correct_query)
    workflow.add_node("web_search", web_search)
    workflow.add_node("generate_answer", generate_answer)
    
    workflow.set_entry_point("rewrite_query")
    
    workflow.add_edge("rewrite_query", "hybrid_retrieve")
    workflow.add_edge("hybrid_retrieve", "evaluate_retrieval")
    workflow.add_conditional_edges(
        "evaluate_retrieval",
        route_after_evaluation,
        {
            "generate_answer": "generate_answer",
            "correct_query": "correct_query",
            "web_search": "web_search"
        }
    )
    workflow.add_edge("correct_query", "hybrid_retrieve")
    workflow.add_edge("web_search", "generate_answer")
    workflow.add_edge("generate_answer", END)
    
    return workflow.compile(checkpointer=checkpointer)
