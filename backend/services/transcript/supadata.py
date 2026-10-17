import logging
from typing import Tuple, List, Dict, Any

from backend.config import SUPADATA_KEYS

logger = logging.getLogger(__name__)

# Track active key index across calls so that once a key runs out / exhausts quota,
# subsequent requests immediately start with the next working key without re-attempting dead keys.
_active_key_index: int = 0


def get_current_key_info() -> Dict[str, Any]:
    """Return status of configured Supadata keys and the currently active key index."""
    num_keys = len(SUPADATA_KEYS)
    curr_idx = _active_key_index % num_keys if num_keys > 0 else 0
    return {
        "total_keys": num_keys,
        "active_key_number": curr_idx + 1 if num_keys > 0 else 0,
        "active_key_preview": (SUPADATA_KEYS[curr_idx][:8] + "...") if num_keys > 0 else "None",
    }


def fetch_from_supadata(video_id: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Fetch YouTube video transcript via Supadata with intelligent multi-key rotation and automated failover.
    - Cloud-ready with residential proxies (prevents datacenter IP blocks on AWS EC2, Docker).
    - If a key runs out (quota reached, 429, payment required, or unauthorized), it automatically rotates
      to the next key and keeps the working key active for subsequent requests.
    - Zero disk persistence.
    """
    global _active_key_index
    from supadata import Supadata, SupadataError

    if not SUPADATA_KEYS:
        raise Exception(
            "No Supadata API keys configured. Please add SUPADATA_KEY_ONE, SUPADATA_KEY_TWO, "
            "SUPADATA_KEY_THREE, or SUPADATA_KEY_FOUR in your .env file."
        )

    num_keys = len(SUPADATA_KEYS)
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    attempts = []

    # Try all keys starting from the current active key
    start_index = _active_key_index % num_keys
    for offset in range(num_keys):
        current_idx = (start_index + offset) % num_keys
        api_key = SUPADATA_KEYS[current_idx]
        key_num = current_idx + 1

        try:
            client = Supadata(api_key=api_key)

            # First attempt: prioritize English captions ("en")
            result = None
            try:
                result = client.transcript(url=video_url, lang="en", mode="auto")
                if not getattr(result, "content", None):
                    result = None
                else:
                    logger.info(f"Retrieved English transcript for video {video_id} via Supadata Key #{key_num}.")
            except Exception as en_err:
                logger.debug(f"English transcript not available for {video_id} ({en_err}), falling back to default language...")
                result = None

            # Fallback attempt: use default/native language if English is not available
            if not result:
                try:
                    result = client.transcript(url=video_url, mode="native")
                except Exception as native_err:
                    logger.debug(f"Supadata native mode with key #{key_num} failed: {native_err}, trying auto mode...")
                    try:
                        result = client.transcript(url=video_url, mode="auto")
                    except Exception:
                        result = client.youtube.transcript(video_id=video_id)

            content = getattr(result, "content", None)
            if not content:
                raise Exception("Empty transcript content returned.")

            segments = [
                {
                    "text": getattr(chunk, "text", str(chunk)).strip(),
                    "start": round(float(getattr(chunk, "offset", 0)) / 1000, 2),
                    "duration": round(float(getattr(chunk, "duration", 0)) / 1000, 2),
                }
                for chunk in content
                if getattr(chunk, "text", str(chunk)).strip()
            ]

            if not segments:
                raise Exception("No transcript segments found in response.")

            full_text = " ".join(seg["text"] for seg in segments)

            # Successfully extracted! Update active key index to this successful key
            _active_key_index = current_idx
            logger.info(
                f"Successfully extracted transcript via Supadata (Key #{key_num} of {num_keys}) "
                f"for {video_id} ({len(segments)} segments)."
            )
            return full_text, segments

        except SupadataError as error:
            err_msg = getattr(error, "message", str(error))
            logger.warning(
                f"Supadata Key #{key_num} of {num_keys} exhausted or failed: {err_msg}. "
                f"Auto-switching to next available key..."
            )
            attempts.append(f"Key #{key_num}: {err_msg}")
            _active_key_index = (current_idx + 1) % num_keys

        except Exception as error:
            err_msg = str(error)
            logger.warning(
                f"Supadata Key #{key_num} of {num_keys} encountered error: {err_msg}. "
                f"Auto-switching to next available key..."
            )
            attempts.append(f"Key #{key_num}: {err_msg}")
            _active_key_index = (current_idx + 1) % num_keys

    # All keys failed
    detail = " | ".join(attempts)
    raise Exception(
        f"All {num_keys} Supadata API keys were tried and failed for video '{video_id}'. Details: {detail}"
    )


def fetch_transcript(video_id: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Fetch YouTube video transcript via Supadata with multi-key auto-failover."""
    return fetch_from_supadata(video_id)
