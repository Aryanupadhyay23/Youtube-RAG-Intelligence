from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import asyncio
import logging
from langgraph.checkpoint.memory import MemorySaver
from contextlib import asynccontextmanager

from backend.core.graph import build_langgraph
from backend.core.vectorstore import build_retrievers
from backend.core.summary import generate_summary
from backend.services.transcript_service import fetch_transcript
from backend.services.youtube_service import get_video_metadata, extract_video_id

# Powered by Ollama for both Chat & Summaries
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # In-memory checkpointer for conversation memory
    app.state.checkpointer = MemorySaver()
    app.state.rag_graph = build_langgraph(checkpointer=app.state.checkpointer)
    yield


app = FastAPI(title="YouTube RAG Intelligence API", lifespan=lifespan)

# Allow CORS for local and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache for vector stores and retrievers
app.state.video_stores = {}


# ── Schemas ──────────────────────────────────────────────────────────────────

class InitRequest(BaseModel):
    video_id: str
    transcript_text: str = ""
    transcript_segments: List[Dict[str, Any]] = []


class ChatRequest(BaseModel):
    video_id: str
    chat_id: str
    query: str
    chat_history: List[Dict[str, str]] = []


class SummaryRequest(BaseModel):
    transcript_text: str


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/health")
@app.get("/api/health")
def health():
    """Health check endpoint for Docker, AWS CodeDeploy, and monitoring."""
    return {"status": "healthy", "service": "YouTube RAG Intelligence Backend"}


@app.post("/init")
async def init_video(req: InitRequest):
    """Initialize a video: fetch transcript, metadata, and build hybrid vector stores."""
    try:
        if req.video_id in app.state.video_stores:
            stored = app.state.video_stores[req.video_id]
            return {
                "status": "already initialized",
                "video_id": req.video_id,
                "metadata": stored.get("metadata", {}),
                "transcript_text": stored.get("transcript_text", ""),
                "transcript_segments": stored.get("transcript_segments", []),
                "segments": len(stored.get("transcript_segments", [])),
            }

        if not req.transcript_segments:
            transcript_text, transcript_segments = await asyncio.to_thread(fetch_transcript, req.video_id)
        else:
            transcript_segments = req.transcript_segments
            transcript_text = req.transcript_text or " ".join(s.get("text", "") for s in transcript_segments)

        metadata = await asyncio.to_thread(get_video_metadata, req.video_id)
        vector_store, bm25_retriever = await asyncio.to_thread(build_retrievers, req.video_id, transcript_segments)

        app.state.video_stores[req.video_id] = {
            "vector_store": vector_store,
            "bm25_retriever": bm25_retriever,
            "metadata": metadata,
            "transcript_text": transcript_text,
            "transcript_segments": transcript_segments,
        }

        return {
            "status": "success",
            "video_id": req.video_id,
            "metadata": metadata,
            "transcript_text": transcript_text,
            "transcript_segments": transcript_segments,
            "segments": len(transcript_segments),
        }
    except Exception as e:
        logger.error(f"Error initializing video {req.video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Stream chat response and graph events using Server-Sent Events (SSE)."""
    if req.video_id not in app.state.video_stores:
        return {"error": "Video not initialized. Call /init first."}

    stores = app.state.video_stores[req.video_id]

    inputs = {
        "query": req.query,
        "rewritten_query": req.query,
        "chat_history": req.chat_history,
        "video_id": req.video_id,
        "retrieval_attempt": 0,
        "retrieved_documents": [],
        "retrieval_score": "",
        "context": "",
        "answer": "",
    }

    thread_id = f"{req.video_id}_{req.chat_id}"
    config = {
        "configurable": {
            "thread_id": thread_id,
            "vector_store": stores["vector_store"],
            "bm25_retriever": stores["bm25_retriever"],
            "llm": __import__("backend.core.llm", fromlist=["load_llm"]).load_llm(),
        }
    }

    async def event_generator():
        try:
            async for event in app.state.rag_graph.astream_events(inputs, config=config, version="v1"):
                kind = event["event"]
                name = event["name"]

                # Stream graph node transitions
                if kind == "on_chain_start" and name in [
                    "rewrite_query", "hybrid_retrieve", "evaluate_retrieval",
                    "correct_query", "web_search", "generate_answer"
                ]:
                    yield f"event: status\ndata: {json.dumps({'message': f'Starting node: {name}'})}\n\n"

                # Stream token chunks from the LLM
                elif kind == "on_chat_model_stream":
                    chunk = event["data"]["chunk"].content
                    if isinstance(chunk, list):
                        chunk = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in chunk)
                    if chunk:
                        yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"

            yield "event: end\ndata: {}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/summary")
async def summarize(req: SummaryRequest):
    """Generate smart summary using single-pass or map-reduce."""
    try:
        summary_text = await asyncio.to_thread(generate_summary, req.transcript_text)
        return {"summary": summary_text}
    except Exception as e:
        logger.error(f"Summary generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
