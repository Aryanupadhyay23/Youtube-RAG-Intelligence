import os
import re
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.core.llm import load_llm
from backend.core.graph import build_langgraph
from backend.core.vectorstore import build_retrievers
from backend.core.summary import generate_summary, generate_summary_async, generate_summary_stream
from backend.core.cache import EphemeralVideoStoreCache
from backend.services.transcript_service import fetch_transcript
from backend.services.youtube_service import get_video_metadata, extract_video_id
from backend.utils.logger import setup_logging, get_available_log_dates, get_datewise_logs_markdown

# Initialize datewise Markdown logger
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pure stateless LangGraph execution (prevents RAM leaks from storing turns in MemorySaver)
    app.state.rag_graph = build_langgraph()

    # Periodic background task to sweep inactive videos from RAM
    stop_event = asyncio.Event()

    async def periodic_cleanup():
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=300)
                break
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                break
            try:
                cleaned = app.state.video_stores.cleanup_expired()
                if cleaned > 0:
                    logger.info(f"Periodic sweep: Purged {cleaned} inactive video(s) from RAM.")
            except Exception as e:
                logger.warning(f"Error during periodic memory cleanup: {e}")

    # Periodic background task to ping public URL every 24 hours to prevent Space from sleeping
    async def keep_alive_heartbeat():
        import urllib.request
        public_space_url = os.environ.get(
            "SPACE_HOST",
            os.environ.get("SPACE_URL", "https://aryan2301-youtube-rag-intelligence.hf.space")
        )
        if not public_space_url.startswith("http"):
            public_space_url = f"https://{public_space_url}"

        while not stop_event.is_set():
            try:
                # Wait 24 hours (86,400 seconds) between pings
                await asyncio.wait_for(stop_event.wait(), timeout=86400)
                break
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                break

            try:
                ping_url = f"{public_space_url.rstrip('/')}/_stcore/health"
                req = urllib.request.Request(
                    ping_url,
                    headers={"User-Agent": "HuggingFace-KeepAlive/1.0"}
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    logger.info(f"24-Hour Keep-Alive ping sent to {ping_url} (HTTP {resp.status}). Inactivity timer reset.")
            except Exception as e:
                logger.debug(f"Keep-alive ping attempt: {e}")

    cleanup_task = asyncio.create_task(periodic_cleanup())
    heartbeat_task = asyncio.create_task(keep_alive_heartbeat())
    try:
        yield
    finally:
        stop_event.set()
        cleanup_task.cancel()
        heartbeat_task.cancel()
        try:
            await asyncio.gather(cleanup_task, heartbeat_task, return_exceptions=True)
        except Exception:
            pass
        app.state.video_stores.clear()


app = FastAPI(title="YouTube RAG Intelligence API", lifespan=lifespan)

# Allow CORS for local and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 100% In-Memory Ephemeral Cache with capacity + inactivity TTL eviction
app.state.video_stores = EphemeralVideoStoreCache()



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

@app.get("/keep-alive")
@app.get("/api/keep-alive")
@app.get("/ping")
def keep_alive():
    """Heartbeat endpoint to keep Hugging Face Space awake and prevent 48-hour sleep."""
    import time
    now_str = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    logger.info(f"Keep-alive heartbeat received at {now_str}.")
    return {
        "status": "alive",
        "timestamp": now_str,
        "service": "YouTube RAG Intelligence",
        "message": "Space is awake and active."
    }


@app.get("/health")
@app.get("/api/health")
def health():
    """Health check endpoint for Docker, AWS CodeDeploy, and monitoring."""
    return {"status": "healthy", "service": "YouTube RAG Intelligence Backend"}


@app.post("/reset")
async def reset_cache(video_id: str = ""):
    """Explicitly evict a specific video vector store from RAM."""
    if not video_id:
        raise HTTPException(status_code=400, detail="video_id is required to evict a session.")
    app.state.video_stores.evict(video_id)
    return {"status": "evicted", "video_id": video_id}


@app.get("/api/logs/dates")
def get_log_dates():
    """Retrieve all available datewise log dates."""
    return {"dates": get_available_log_dates()}


@app.get("/api/logs")
def get_logs(date: str = "", level: str = "", query: str = ""):
    """Retrieve datewise logs formatted in clean Markdown."""
    if date and not re.fullmatch(r"^\d{4}-\d{2}-\d{2}$", date):
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")
    md_content = get_datewise_logs_markdown(date_str=date or None, level_filter=level or None, search_query=query)
    return {"markdown": md_content, "date": date}




@app.post("/init")
async def init_video(req: InitRequest):
    """Initialize a video: fetch transcript, metadata, and build hybrid vector stores."""
    try:
        # Check cache (in-memory LRU or lazy-loaded from persistent disk)
        cached_entry = app.state.video_stores.get(req.video_id)
        if cached_entry:
            logger.info(f"Video '{req.video_id}' loaded from cache.")
            return {
                "status": "already initialized",
                "video_id": req.video_id,
                "metadata": cached_entry.get("metadata", {}),
                "transcript_text": cached_entry.get("transcript_text", ""),
                "transcript_segments": cached_entry.get("transcript_segments", []),
                "segments": len(cached_entry.get("transcript_segments", [])),
            }

        # Fetch transcript via primary (youtube_transcript_api) or fallback (Supadata)
        if not req.transcript_segments:
            transcript_text, transcript_segments = await asyncio.to_thread(fetch_transcript, req.video_id)
        else:
            transcript_segments = req.transcript_segments
            transcript_text = req.transcript_text or " ".join(s.get("text", "") for s in transcript_segments)

        metadata = await asyncio.to_thread(get_video_metadata, req.video_id)
        vector_store, bm25_retriever = await asyncio.to_thread(build_retrievers, req.video_id, transcript_segments)

        store_entry = {
            "vector_store": vector_store,
            "bm25_retriever": bm25_retriever,
            "metadata": metadata,
            "transcript_text": transcript_text,
            "transcript_segments": transcript_segments,
        }

        # Store in two-tier LRU cache and persistent disk storage
        app.state.video_stores.put(req.video_id, store_entry)

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
    stores = app.state.video_stores.get(req.video_id)
    if not stores:
        async def not_initialized_stream():
            yield f"event: error\ndata: {json.dumps({'error': 'Video not initialized. Call /init first.'})}\n\n"
        return StreamingResponse(not_initialized_stream(), media_type="text/event-stream")

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
            "llm": load_llm(),
        }
    }

    async def event_generator():
        app.state.video_stores.acquire(req.video_id)
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

                # Stream token chunks from the LLM only for final answer generation
                elif kind == "on_chat_model_stream":
                    current_node = event.get("metadata", {}).get("langgraph_node")
                    if current_node and current_node != "generate_answer":
                        continue
                    chunk = event["data"]["chunk"].content
                    if isinstance(chunk, list):
                        chunk = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in chunk)
                    if chunk:
                        yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"

            yield "event: end\ndata: {}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        finally:
            app.state.video_stores.release(req.video_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/summary/stream")
async def summarize_stream(req: SummaryRequest):
    """Stream smart summary generation progress events and final tokens via SSE."""
    async def event_generator():
        try:
            async for event in generate_summary_stream(req.transcript_text):
                event_type = event.get("type", "status")
                if event_type == "status":
                    yield f"event: status\ndata: {json.dumps({'message': event.get('message', '')})}\n\n"
                elif event_type == "token":
                    yield f"event: token\ndata: {json.dumps({'token': event.get('token', '')})}\n\n"
                elif event_type == "end":
                    yield "event: end\ndata: {}\n\n"
        except Exception as e:
            logger.error(f"Streaming summary error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/summary")
async def summarize(req: SummaryRequest):
    """Generate smart summary using parallel map-reduce."""
    try:
        summary_text = await generate_summary_async(req.transcript_text)
        return {"summary": summary_text}
    except Exception as e:
        logger.error(f"Summary generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
