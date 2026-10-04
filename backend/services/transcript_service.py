import logging
from supadata import Supadata, SupadataError
from backend.config import SUPADATA_KEYS

logger = logging.getLogger(__name__)


def fetch_transcript(video_id: str):
    """
    Fetch YouTube video transcript via Supadata with automated multi-key failover.
    Returns: (full_plain_text, list_of_timestamped_segments)
    """
    if not SUPADATA_KEYS:
        raise Exception("No Supadata API keys configured.")

    last_error = "Unknown error"
    for api_key in SUPADATA_KEYS:
        try:
            client = Supadata(api_key=api_key)
            result = client.youtube.transcript(video_id=video_id, lang="en")

            if not getattr(result, "content", None):
                raise Exception("Empty transcript returned.")

            segments = [
                {
                    "text": getattr(chunk, "text", str(chunk)).strip(),
                    "start": getattr(chunk, "offset", 0) / 1000,
                    "duration": getattr(chunk, "duration", 0) / 1000,
                }
                for chunk in result.content
                if getattr(chunk, "text", str(chunk)).strip()
            ]

            if not segments:
                raise Exception("No transcript segments found.")

            return " ".join(seg["text"] for seg in segments), segments

        except SupadataError as error:
            last_error = getattr(error, "message", str(error))
            logger.warning(f"Supadata key failed: {last_error}, attempting next key...")
        except Exception as error:
            last_error = str(error)
            logger.warning(f"Transcript fetch error: {last_error}, attempting next key...")

    raise Exception(f"All Supadata API keys failed. Last error: {last_error}")
