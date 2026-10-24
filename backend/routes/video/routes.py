import re
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Request
from backend.routes.video.schemas import InitRequest
from backend.services.transcript import fetch_transcript
from backend.services.youtube import get_video_metadata
from backend.core.ingestion import (
    QdrantUnavailable,
    QdrantVideoCache,
    build_bm25_retriever,
    create_timestamp_aware_chunks,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Video & Ingestion"])

# Match explicit "no transcript / captions unavailable" errors only, so unrelated
# failures (network, auth, server errors) are not misreported as 404s.
_NO_TRANSCRIPT_PATTERN = re.compile(
    r"\b(?:"
    r"no[\s-]+(?:transcript|transcripts|captions?|subtitles?)"
    r"|empty[\s-]+transcript"
    r"|(?:transcript|captions?|subtitles?)[\s-]+(?:(?:is|are)[\s-]+)?(?:unavailable|not[\s-]+(?:available|found))"
    r")\b",
    re.IGNORECASE,
)


def _get_video_stores(request: Request):
    if not hasattr(request.app.state, "video_stores") or request.app.state.video_stores is None:
        from backend.core.ingestion import EphemeralVideoStoreCache

        request.app.state.video_stores = EphemeralVideoStoreCache()
    return request.app.state.video_stores


def _get_qdrant_cache(app) -> QdrantVideoCache:
    """Get the Qdrant Cloud cache instance from app state."""
    if not hasattr(app.state, "qdrant_video_cache"):
        app.state.qdrant_video_cache = QdrantVideoCache()
    return app.state.qdrant_video_cache


@router.post("/init")
async def init_video(req: InitRequest, request: Request):
    """Initialize a video: fetch transcript, metadata, and build hybrid vector stores."""
    video_stores = _get_video_stores(request)
    init_lock = video_stores.acquire_init_lock(req.video_id)
    acquired = False
    try:
        await init_lock.acquire()
        acquired = True
        return await _initialize_video(req, video_stores, request.app)
    finally:
        if acquired:
            init_lock.release()
        video_stores.release_init_lock(req.video_id)


async def _initialize_video(req: InitRequest, video_stores, app):
    """Initialize a video while holding its per-video lock."""
    try:
        # Check active in-memory cache
        cached_entry = video_stores.get(req.video_id)
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

        qdrant_cache = _get_qdrant_cache(app)
        if not qdrant_cache.enabled:
            raise HTTPException(
                status_code=503,
                detail="Qdrant Cloud is not configured. Please set QDRANT_CLUSTER_ENDPOINT and QDRANT_API_KEY.",
            )

        # Check Qdrant Cloud for previously stored video embeddings
        try:
            persisted = await asyncio.to_thread(qdrant_cache.load_video, req.video_id)
        except QdrantUnavailable as exc:
            logger.error("Qdrant lookup failed for %s: %s", req.video_id, exc)
            raise HTTPException(
                status_code=503,
                detail=f"Qdrant Cloud is currently unavailable: {exc}",
            ) from exc

        if persisted:
            vector_store = qdrant_cache.vector_store_for(req.video_id)
            bm25_retriever = await asyncio.to_thread(build_bm25_retriever, persisted["documents"])
            store_entry = {
                "vector_store": vector_store,
                "bm25_retriever": bm25_retriever,
                "metadata": persisted.get("metadata", {}),
                "transcript_text": persisted.get("transcript_text", ""),
                "transcript_segments": persisted.get("transcript_segments", []),
            }
            video_stores.put(req.video_id, store_entry)
            logger.info("Video '%s' restored from Qdrant Cloud.", req.video_id)
            return {
                "status": "restored from qdrant",
                "video_id": req.video_id,
                "metadata": store_entry["metadata"],
                "transcript_text": store_entry["transcript_text"],
                "transcript_segments": store_entry["transcript_segments"],
                "segments": len(store_entry["transcript_segments"]),
            }

        # Concurrently fetch transcript and video metadata in parallel
        fetch_task = asyncio.to_thread(fetch_transcript, req.video_id)
        meta_task = asyncio.to_thread(get_video_metadata, req.video_id)
        transcript_result, meta_result = await asyncio.gather(fetch_task, meta_task, return_exceptions=True)

        if isinstance(transcript_result, BaseException):
            raise transcript_result
        if isinstance(meta_result, BaseException):
            logger.warning(f"Metadata fetch failed for {req.video_id}: {meta_result}")
            metadata = {}
        else:
            metadata = meta_result
        transcript_text, transcript_segments = transcript_result

        # Index video into Qdrant Cloud and build BM25 retriever
        documents = await asyncio.to_thread(create_timestamp_aware_chunks, req.video_id, transcript_segments)
        if not documents:
            raise ValueError("No valid chunks created from transcript segments.")

        try:
            vector_store = await asyncio.to_thread(
                qdrant_cache.store_video,
                req.video_id,
                documents,
                metadata,
                transcript_text,
                transcript_segments,
            )
        except QdrantUnavailable as exc:
            logger.error("Qdrant storage failed for %s: %s", req.video_id, exc)
            raise HTTPException(
                status_code=503,
                detail=f"Failed to persist video in Qdrant Cloud: {exc}",
            ) from exc

        bm25_retriever = await asyncio.to_thread(build_bm25_retriever, documents)
        logger.info("Video '%s' embedded and stored in Qdrant Cloud.", req.video_id)

        store_entry = {
            "vector_store": vector_store,
            "bm25_retriever": bm25_retriever,
            "metadata": metadata,
            "transcript_text": transcript_text,
            "transcript_segments": transcript_segments,
        }

        # Store in ephemeral video store cache
        video_stores.put(req.video_id, store_entry)

        return {
            "status": "success",
            "video_id": req.video_id,
            "metadata": metadata,
            "transcript_text": transcript_text,
            "transcript_segments": transcript_segments,
            "segments": len(transcript_segments),
        }
    except HTTPException:
        # Preserve explicit 4xx/5xx responses raised above (for example Qdrant
        # configuration or connection failures) instead of rewriting them as 500.
        raise
    except Exception as e:
        if _NO_TRANSCRIPT_PATTERN.search(str(e)):
            logger.info(f"No transcript available for video {req.video_id}: {e}")
            raise HTTPException(
                status_code=404,
                detail="Transcript not available for this video. It may be private, blocked, or lack captions.",
            ) from e
        logger.error(f"Error initializing video {req.video_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to initialize video. Please try again shortly.",
        ) from e


@router.post("/reset")
async def reset_cache(request: Request, video_id: str = ""):
    """Explicitly evict a specific video vector store from RAM."""
    if not video_id:
        raise HTTPException(status_code=400, detail="video_id is required to evict a session.")
    _get_video_stores(request).evict(video_id)
    return {"status": "evicted", "video_id": video_id}
