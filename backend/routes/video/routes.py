import re
import asyncio
import logging
from fastapi import APIRouter, HTTPException, Request
from backend.routes.video.schemas import InitRequest
from backend.services.transcript import fetch_transcript
from backend.services.youtube import get_video_metadata
from backend.core.ingestion import build_retrievers

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


@router.post("/init")
async def init_video(req: InitRequest, request: Request):
    """Initialize a video: fetch transcript, metadata, and build hybrid vector stores."""
    video_stores = _get_video_stores(request)
    init_lock = video_stores.acquire_init_lock(req.video_id)
    acquired = False
    try:
        await init_lock.acquire()
        acquired = True
        return await _initialize_video(req, video_stores)
    finally:
        if acquired:
            init_lock.release()
        video_stores.release_init_lock(req.video_id)


async def _initialize_video(req: InitRequest, video_stores):
    """Initialize a video while holding its per-video lock."""
    try:
        # Check cache (in-memory LRU or lazy-loaded from persistent disk)
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

        # Concurrently fetch transcript and video metadata in parallel.
        # return_exceptions so the metadata task is always awaited instead of
        # abandoned when the transcript fetch fails.
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

        vector_store, bm25_retriever = await asyncio.to_thread(build_retrievers, req.video_id, transcript_segments)

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
