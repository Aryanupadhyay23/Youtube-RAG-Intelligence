import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.workflow import build_langgraph
from backend.core.checkpointer import get_redis_checkpointer
from backend.config import QDRANT_KEEPALIVE_REQUESTS
from backend.core.ingestion import EphemeralVideoStoreCache, QdrantVideoCache
from backend.utils.logger import setup_logging

# Import modular route handlers from subfolders
from backend.routes.health import router as health_router
from backend.routes.video import router as video_router
from backend.routes.chat import router as chat_router
from backend.routes.summary import router as summary_router
from backend.routes.redis import router as redis_router

# Initialize datewise Markdown logger
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize Redis Checkpointer for LangGraph persistent memory across requests
    app.state.checkpointer = get_redis_checkpointer()
    app.state.rag_graph = build_langgraph(checkpointer=app.state.checkpointer)

    # In-Memory Ephemeral Cache with capacity + inactivity TTL eviction
    app.state.video_stores = EphemeralVideoStoreCache()
    # Construction is local only; the first Cloud operation handles unavailable Qdrant gracefully.
    app.state.qdrant_video_cache = QdrantVideoCache()

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

    cleanup_task = asyncio.create_task(periodic_cleanup())

    async def periodic_qdrant_keepalive():
        """Keep a free-tier Qdrant Cloud cluster active without affecting request handling."""
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=3600)
                break
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                break

            qdrant_cache = app.state.qdrant_video_cache
            if not qdrant_cache.enabled:
                continue
            successes = 0
            for _ in range(QDRANT_KEEPALIVE_REQUESTS):
                if stop_event.is_set():
                    break
                if await asyncio.to_thread(qdrant_cache.ping):
                    successes += 1
            logger.info(
                "Qdrant keepalive finished: %s/%s requests succeeded.",
                successes,
                QDRANT_KEEPALIVE_REQUESTS,
            )

    qdrant_keepalive_task = asyncio.create_task(periodic_qdrant_keepalive())
    try:
        yield
    finally:
        stop_event.set()
        cleanup_task.cancel()
        qdrant_keepalive_task.cancel()
        try:
            await asyncio.gather(cleanup_task, qdrant_keepalive_task, return_exceptions=True)
        except Exception:
            pass
        app.state.video_stores.clear()


app = FastAPI(
    title="YouTube RAG Intelligence API",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow CORS for local and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect modular subfolder routers
app.include_router(health_router)
app.include_router(video_router)
app.include_router(chat_router)
app.include_router(summary_router)
app.include_router(redis_router)


# Root health status
@app.get("/")
async def read_root():
    return {
        "status": "healthy",
        "service": "YouTube RAG Intelligence Backend",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
