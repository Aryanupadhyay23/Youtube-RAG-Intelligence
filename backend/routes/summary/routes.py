import json
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.routes.summary.schemas import SummaryRequest
from backend.core.summary import generate_summary_async, generate_summary_stream

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Summarization"])


@router.post("/summary/stream")
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


@router.post("/summary")
async def summarize(req: SummaryRequest):
    """Generate smart summary using parallel map-reduce."""
    try:
        summary_text = await generate_summary_async(req.transcript_text)
        return {"summary": summary_text}
    except Exception as e:
        logger.error(f"Summary generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
