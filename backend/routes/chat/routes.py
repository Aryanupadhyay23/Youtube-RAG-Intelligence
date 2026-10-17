import json
import asyncio
import logging
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from backend.routes.chat.schemas import ChatRequest
from backend.core.llm import load_llm
from backend.services.redis import redis_memory, clean_username
from backend.utils.constants import MEMORY_WINDOW

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat & Streaming"])


def _ensure_app_state(request: Request):
    app_state = request.app.state
    if not hasattr(app_state, "video_stores") or app_state.video_stores is None:
        from backend.core.ingestion import EphemeralVideoStoreCache
        app_state.video_stores = EphemeralVideoStoreCache()
    if not hasattr(app_state, "checkpointer") or app_state.checkpointer is None:
        from backend.core.checkpointer import get_redis_checkpointer
        app_state.checkpointer = get_redis_checkpointer()
    if not hasattr(app_state, "rag_graph") or app_state.rag_graph is None:
        from backend.core.workflow.graph import build_langgraph
        app_state.rag_graph = build_langgraph(checkpointer=app_state.checkpointer)
    return app_state


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    """Stream chat response and graph events using Server-Sent Events (SSE)."""
    app_state = _ensure_app_state(request)
    stores = app_state.video_stores.get(req.video_id)
    if not stores:
        async def not_initialized_stream():
            yield f"event: error\ndata: {json.dumps({'error': 'Video not initialized. Call /init first.'})}\n\n"
        return StreamingResponse(not_initialized_stream(), media_type="text/event-stream")

    clean_user = clean_username(req.username)
    thread_id = f"{clean_user}_{req.video_id}_{req.chat_id}"
    config = {
        "configurable": {
            "thread_id": thread_id,
            "vector_store": stores["vector_store"],
            "bm25_retriever": stores["bm25_retriever"],
            "llm": load_llm(),
        }
    }

    # Check if a LangGraph checkpoint already exists in Redis/RAM for this thread
    existing_tuple = app_state.checkpointer.get_tuple(config)

    inputs = {
        "query": req.query,
        "video_id": req.video_id,
        "retrieval_attempt": 0,
        "retrieved_documents": [],
        "retrieval_score": "",
        "context": "",
        "answer": "",
    }

    # If first turn in checkpointer, hydrate initial turns from Redis
    if not existing_tuple:
        historical_messages = req.chat_history or (
            redis_memory.get_messages(req.chat_id, limit=MEMORY_WINDOW) if req.chat_id else []
        )
        inputs["chat_history"] = historical_messages

    async def event_generator():
        app_state.video_stores.acquire(req.video_id)
        full_answer = ""
        try:
            async for event in app_state.rag_graph.astream_events(inputs, config=config, version="v1"):
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
                        full_answer += chunk
                        yield f"event: token\ndata: {json.dumps({'token': chunk})}\n\n"

            # Persist updated LangGraph checkpoint to Redis
            if hasattr(app_state.checkpointer, "sync_to_redis"):
                try:
                    await asyncio.to_thread(app_state.checkpointer.sync_to_redis, thread_id)
                except Exception as cp_err:
                    logger.warning(f"Failed to sync LangGraph checkpoint to Redis: {cp_err}")

            # Auto-persist conversational turn to Upstash Redis Memory (for UI sidebar list)
            if full_answer:
                try:
                    await asyncio.to_thread(
                        redis_memory.append_turn,
                        video_id=req.video_id,
                        chat_id=req.chat_id,
                        user_query=req.query,
                        ai_response=full_answer,
                        username=req.username,
                    )
                except Exception as save_err:
                    logger.warning(f"Failed to auto-save chat turn to Redis: {save_err}")

            yield "event: end\ndata: {}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
        finally:
            app_state.video_stores.release(req.video_id)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
