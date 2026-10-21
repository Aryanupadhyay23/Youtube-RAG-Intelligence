import asyncio
import logging
from fastapi import APIRouter, HTTPException, Request
from backend.routes.video.schemas import InitRequest
from backend.services.transcript import fetch_transcript
from backend.services.youtube import get_video_metadata
from backend.core.ingestion import build_retrievers

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Video & Ingestion"])


def _get_video_stores(request: Request):
    if not hasattr(request.app.state, "video_stores") or request.app.state.video_stores is None:
        from backend.core.ingestion import EphemeralVideoStoreCache
        request.app.state.video_stores = EphemeralVideoStoreCache()
    return request.app.state.video_stores


@router.post("/init")
async def init_video(req: InitRequest, request: Request):
    """Initialize a video: fetch transcript, metadata, and build hybrid vector stores."""
    try:
        video_stores = _get_video_stores(request)
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

        # Concurrently fetch transcript and video metadata in parallel
        fetch_task = asyncio.to_thread(fetch_transcript, req.video_id)
        meta_task = asyncio.to_thread(get_video_metadata, req.video_id)
        (transcript_text, transcript_segments), metadata = await asyncio.gather(fetch_task, meta_task)

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
        logger.error(f"Error initializing video {req.video_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/reset")
async def reset_cache(request: Request, video_id: str = ""):
    """Explicitly evict a specific video vector store from RAM."""
    if not video_id:
        raise HTTPException(status_code=400, detail="video_id is required to evict a session.")
    _get_video_stores(request).evict(video_id)
    return {"status": "evicted", "video_id": video_id}
