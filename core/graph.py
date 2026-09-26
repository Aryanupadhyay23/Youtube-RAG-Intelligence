import logging
from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from core.retrieval import hybrid_retrieve
from core.prompts import (
    REWRITE_PROMPT, RewriteResult,
    GRADER_PROMPT, GradeResult,
    CORRECTIVE_PROMPT, CorrectResult,
    ANSWER_PROMPT
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

def format_docs_with_timestamps(docs):
    formatted = []
    for doc in docs:
        video_id = doc.metadata.get("video_id")
        start = doc.metadata.get("start_time", 0)
        
        url = get_youtube_timestamp_url(video_id, start) if video_id else ""
        
        formatted.append(f"Content: {doc.page_content}\nSource: {url}")
    return "\n\n".join(formatted)

from langchain_core.runnables import RunnableConfig

async def _rephrase_query(state: RAGState, prompt, output_schema, llm, **kwargs) -> RAGState:
    query = state.get("rewritten_query", state["query"])
    history = state.get("chat_history", [])
    
    native_history = []
    for h in history:
        native_history.append(HumanMessage(content=h['user']))
        native_history.append(AIMessage(content=h['ai']))
    
    structured_llm = llm.with_structured_output(output_schema)
    messages = prompt.format_messages(chat_history=native_history, **kwargs)
    
    response = await structured_llm.ainvoke(messages)
    
    # Extract the rephrased query regardless of the specific schema attribute
    new_query = getattr(response, "standalone_query", getattr(response, "corrected_query", query))
    if hasattr(response, "needs_rewrite") and not response.needs_rewrite:
        new_query = query
        
    logger.info(f"Query updated: '{query}' -> '{new_query}'")
    return {"rewritten_query": new_query}

async def rewrite_query(state: RAGState, config: RunnableConfig) -> RAGState:
    if not state.get("chat_history"):
        return {"rewritten_query": state["query"]}
    llm = config["configurable"]["llm"]
    return await _rephrase_query(state, REWRITE_PROMPT, RewriteResult, llm, question=state["query"])

async def hybrid_retrieve_node(state: RAGState, config: RunnableConfig) -> RAGState:
    query = state.get("rewritten_query", state["query"])
    vector_store = config["configurable"]["vector_store"]
    bm25 = config["configurable"]["bm25_retriever"]
    attempt = state.get("retrieval_attempt", 0) + 1
    
    docs = await hybrid_retrieve(query, vector_store, bm25)
    
    logger.info(f"Retrieval attempt {attempt}: found {len(docs)} documents.")
    return {"retrieved_documents": docs, "retrieval_attempt": attempt}

async def evaluate_retrieval(state: RAGState, config: RunnableConfig) -> RAGState:
    docs = state.get("retrieved_documents", [])
    query = state.get("rewritten_query", state["query"])
    llm = config["configurable"]["llm"]
    
    if not docs:
        return {"retrieval_score": "POOR"}
        
    top_doc = docs[0].page_content
    structured_llm = llm.with_structured_output(GradeResult)
    messages = GRADER_PROMPT.format_messages(question=query, document=top_doc)
    
    response = await structured_llm.ainvoke(messages)
    
    grade = "GOOD" if response.relevant else "POOR"
    logger.info(f"Retrieval graded as: {grade} (Score: {response.score}, Reason: {response.reason})")
    return {"retrieval_score": grade}

async def correct_query(state: RAGState, config: RunnableConfig) -> RAGState:
    llm = config["configurable"]["llm"]
    return await _rephrase_query(
        state, CORRECTIVE_PROMPT, CorrectResult, llm,
        original_query=state["query"], failed_query=state.get("rewritten_query", state["query"])
    )

async def web_search(state: RAGState) -> RAGState:
    query = state.get("rewritten_query", state["query"])
    results = await fallback_web_search(query)
    logger.info("Web search used as fallback.")
    return {"context": f"[WEB SEARCH RESULTS]\n{results}"}

async def generate_answer(state: RAGState, config: RunnableConfig) -> RAGState:
    if not state.get("context") and state.get("retrieved_documents"):
        state["context"] = format_docs_with_timestamps(state["retrieved_documents"])
        
    context = state.get("context", "")
    query = state.get("rewritten_query", state["query"])
    history = state.get("chat_history", [])
    
    native_history = []
    for h in history:
        native_history.append(HumanMessage(content=h['user']))
        native_history.append(AIMessage(content=h['ai']))
        
    messages = ANSWER_PROMPT.format_messages(
        context=context,
        chat_history=native_history,
        query=query
    )
    
    llm = config["configurable"]["llm"]
    response = await llm.ainvoke(messages, config)
    
    answer_text = response.content
    if isinstance(answer_text, list):
        answer_text = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in answer_text)
        
    return {"answer": answer_text}

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
