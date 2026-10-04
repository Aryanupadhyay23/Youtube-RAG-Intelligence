import os
import logging
from backend.config import SUPADATA_KEYS

logger = logging.getLogger(__name__)


def _fetch_from_supadata(video_id: str):
    """
    Fetch YouTube video transcript via Supadata with automated multi-key failover.
    Supadata uses residential proxy networks, making it resilient to datacenter IP blocks
    on cloud environments such as AWS EC2, HuggingFace Spaces, GCP, and Docker.
    
    Supports native language captions without forcing English.
    """
    from supadata import Supadata, SupadataError

    if not SUPADATA_KEYS:
        raise Exception("No Supadata API keys configured.")

    last_error = "Unknown error"
    for idx, api_key in enumerate(SUPADATA_KEYS, 1):
        try:
            client = Supadata(api_key=api_key)

            # Attempt native language transcript first (lang=None)
            result = None
            try:
                result = client.youtube.transcript(video_id=video_id)
            except Exception as lang_err:
                logger.debug(f"Supadata fetch without lang failed: {lang_err}, attempting with lang='en'...")
                result = client.youtube.transcript(video_id=video_id, lang="en")

            if not getattr(result, "content", None):
                raise Exception("Empty transcript content returned from Supadata.")

            segments = [
                {
                    "text": getattr(chunk, "text", str(chunk)).strip(),
                    "start": round(float(getattr(chunk, "offset", 0)) / 1000, 2),
                    "duration": round(float(getattr(chunk, "duration", 0)) / 1000, 2),
                }
                for chunk in result.content
                if getattr(chunk, "text", str(chunk)).strip()
            ]

            if not segments:
                raise Exception("No transcript segments found in Supadata response.")

            logger.info(f"Successfully fetched transcript via Supadata (Key #{idx}) for {video_id} ({len(segments)} segments).")
            return " ".join(seg["text"] for seg in segments), segments

        except SupadataError as error:
            last_error = getattr(error, "message", str(error))
            logger.warning(f"Supadata key #{idx} failed: {last_error}, attempting next key...")
        except Exception as error:
            last_error = str(error)
            logger.warning(f"Supadata fetch error with key #{idx}: {last_error}, attempting next key...")

    raise Exception(f"All Supadata API keys failed. Last error: {last_error}")


def _fetch_from_youtube_transcript_api(video_id: str):
    """
    Secondary / Local fallback using youtube_transcript_api.
    Note: YouTube actively blocks datacenter IP ranges (AWS EC2, GCP, HuggingFace Spaces).
    This engine works best for local development or when a custom proxy is provided via YOUTUBE_PROXY / HTTP_PROXY.
    """
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api.proxies import GenericProxyConfig

        proxy_url = os.environ.get("YOUTUBE_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")
        proxy_config = GenericProxyConfig(http_url=proxy_url, https_url=proxy_url) if proxy_url else None

        yta = YouTubeTranscriptApi(proxy_config=proxy_config)
        transcript_list = yta.list(video_id)

        # 1. Look for English transcript first (manual or auto-generated)
        target_transcript = None
        for lang_code in ["en", "en-US", "en-GB", "en-CA", "en-AU"]:
            try:
                target_transcript = transcript_list.find_transcript([lang_code])
                if target_transcript:
                    break
            except Exception:
                continue

        # 2. If no English transcript found, pick the first available transcript (native language)
        if not target_transcript:
            target_transcript = next(iter(transcript_list), None)

        if not target_transcript:
            raise Exception("No transcripts found in transcript list.")

        logger.info(
            f"Found transcript via youtube_transcript_api for {video_id} "
            f"(Language: {target_transcript.language} [{target_transcript.language_code}], "
            f"Generated: {target_transcript.is_generated})"
        )

        fetched = target_transcript.fetch()
        segments = []
        for snippet in fetched:
            text = getattr(snippet, "text", "") if hasattr(snippet, "text") else snippet.get("text", "")
            start = getattr(snippet, "start", 0.0) if hasattr(snippet, "start") else snippet.get("start", 0.0)
            duration = getattr(snippet, "duration", 0.0) if hasattr(snippet, "duration") else snippet.get("duration", 0.0)

            clean_text = str(text).strip()
            if clean_text:
                segments.append({
                    "text": clean_text,
                    "start": round(float(start), 2),
                    "duration": round(float(duration), 2),
                })

        if not segments:
            raise Exception("Empty transcript fetched.")

        full_text = " ".join(seg["text"] for seg in segments)
        return full_text, segments

    except Exception as e:
        logger.warning(f"youtube_transcript_api could not fetch transcript for {video_id}: {e}")
        return None, None


def fetch_transcript(video_id: str):
    """
    Fetch YouTube video transcript in any language with cloud-first proxy resilience:
    1. Primary (Cloud-ready): Supadata API with multi-key rotation and residential proxy network
       (Reliable on AWS EC2, Hugging Face Spaces, GCP, Azure, and Docker without IP blocks).
    2. Fallback (Local / Proxy): youtube_transcript_api (Free fallback for local machines or custom proxies).
    
    Returns: (full_plain_text, list_of_timestamped_segments)
    """
    # 1. Primary: Use Supadata if keys are configured (recommended for EC2 and HuggingFace Spaces)
    if SUPADATA_KEYS:
        try:
            return _fetch_from_supadata(video_id)
        except Exception as supadata_err:
            logger.warning(
                f"Supadata primary fetch failed for video '{video_id}': {supadata_err}. "
                "Attempting fallback to youtube-transcript-api..."
            )

    # 2. Fallback: youtube_transcript_api (for local dev or if Supadata fails/is unconfigured)
    text, segments = _fetch_from_youtube_transcript_api(video_id)
    if text and segments:
        return text, segments

    # Both engines failed
    raise Exception(
        f"Unable to retrieve transcript for video '{video_id}'. "
        "Cloud primary (Supadata) failed or is not configured, and direct YouTube caption extraction "
        "was blocked (common on cloud/datacenter IPs) or captions are disabled for this video."
    )
