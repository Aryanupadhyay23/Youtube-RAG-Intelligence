from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import asyncio
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager

from core.graph import build_langgraph
from core.vectorstore import build_retrievers
from services.transcript_service import fetch_transcript

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize async SQLite connection and checkpointer on startup
    app.state.sqlite_conn = await aiosqlite.connect("api_checkpoints.sqlite", check_same_thread=False)
    app.state.checkpointer = AsyncSqliteSaver(app.state.sqlite_conn)
    app.state.rag_graph = build_langgraph(checkpointer=app.state.checkpointer)
    yield
    # Cleanup on shutdown
    await app.state.sqlite_conn.close()

app = FastAPI(title="YouTube RAG Intelligence API", lifespan=lifespan)

# Simple in-memory cache for vector stores and retrievers
# In production, use Redis or a persistent ChromaDB path
app.state.video_stores = {}

# In production, use Redis or a persistent ChromaDB path
app.state.video_stores = {}

class InitRequest(BaseModel):
    video_id: str
    transcript_segments: List[Dict[str, Any]] = []

class ChatRequest(BaseModel):
    video_id: str
    chat_id: str
    query: str
    chat_history: List[Dict[str, str]] = []

@app.post("/init")
async def init_video(req: InitRequest):
    """Initialize a video: fetch transcript and build vector store."""
    if req.video_id in app.state.video_stores:
        return {"status": "already initialized"}
        
    if not req.transcript_segments:
        transcript_text, transcript_segments = await asyncio.to_thread(fetch_transcript, req.video_id)
    else:
        transcript_segments = req.transcript_segments
        
    vector_store, bm25_retriever = await asyncio.to_thread(build_retrievers, req.video_id, transcript_segments)
    
    app.state.video_stores[req.video_id] = {
        "vector_store": vector_store,
        "bm25_retriever": bm25_retriever
    }
    
    return {"status": "success", "segments": len(transcript_segments)}

@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Stream chat response and graph events using Server-Sent Events (SSE)."""
    
    if req.video_id not in app.state.video_stores:
        return {"error": "Video not initialized. Call /init first."}
        
    stores = app.state.video_stores[req.video_id]
    
    inputs = {
        "query": req.query,
        "chat_history": req.chat_history,
        "video_id": req.video_id,
        "vector_store": stores["vector_store"],
        "bm25_retriever": stores["bm25_retriever"],
        # LLM needs to be initialized. We can import here to avoid global init issues.
        "llm": __import__("core.llm", fromlist=["load_llm"]).load_llm(),
        "retrieval_attempt": 0,
        "context": ""
    }
    
    thread_id = f"{req.video_id}_{req.chat_id}"
    config = {"configurable": {"thread_id": thread_id}}

    async def event_generator():
        # Yield meaningful Server-Sent Events (SSE) by streaming the graph execution
        try:
            async for event in app.state.rag_graph.astream_events(inputs, config=config, version="v1"):
                kind = event["event"]
                name = event["name"]
                
                # Stream graph node transitions (e.g., hybrid_retrieve, evaluate_retrieval)
                if kind == "on_chain_start" and name in ["hybrid_retrieve", "evaluate_retrieval", "correct_query", "web_search", "generate_answer"]:
                    yield f"event: status\ndata: {json.dumps({'message': f'Starting node: {name}'})}\n\n"
                    
                # Stream the actual tokens from the LLM inside generate_answer
                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    if chunk:
                        yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"
                        
            yield "event: end\ndata: {}\n\n"
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
