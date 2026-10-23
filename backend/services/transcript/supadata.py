import logging
import re
import threading
from typing import Tuple, List, Dict, Any

from backend.config import SUPADATA_KEYS

logger = logging.getLogger(__name__)

# Supadata error codes that indicate a dead/exhausted key (HTTP 401, 402, 429).
_RETRYABLE_ERROR_CODES = {"unauthorized", "upgrade-required", "limit-exceeded"}

# Fallback for errors without a Supadata error code (e.g. requests.HTTPError).
# Numeric statuses only match when they appear as an HTTP status, so unrelated
# numbers inside a message do not trigger key rotation.
_RETRYABLE_MESSAGE_PATTERNS = (
    r"\bunauthorized\b",
    r"\bpayment required\b",
    r"\bupgrade required\b",
    r"\bquota\b",
    r"\brate limit\b",
    r"\btoo many requests\b",
    r"\bhttp (?:401|402|429)\b",
    r"\b(?:401|402|429) (?:client error|unauthorized|payment required|too many requests)\b",
)


def _is_retryable_error(error: Exception) -> bool:
    """Return True only when the error means the current API key should be rotated."""
    code = str(getattr(error, "error", "") or "").strip().lower()
    if code:
        return code in _RETRYABLE_ERROR_CODES

    text = " ".join(
        str(part)
        for part in (
            getattr(error, "message", ""),
            getattr(error, "details", ""),
            str(error),
        )
        if part
    ).lower()
    return any(re.search(pattern, text) for pattern in _RETRYABLE_MESSAGE_PATTERNS)


# Track active key index across calls so that once a key runs out / exhausts quota,
# subsequent requests immediately start with the next working key without re-attempting dead keys.
_active_key_index: int = 0
_active_key_lock = threading.Lock()


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
    with _active_key_lock:
        start_index = _active_key_index % num_keys
    for offset in range(num_keys):
        current_idx = (start_index + offset) % num_keys
        api_key = SUPADATA_KEYS[current_idx]
        key_num = current_idx + 1

        try:
            client = Supadata(api_key=api_key)

            # First attempt: prioritize English captions ("en")
            result = None
            last_error = None
            try:
                result = client.transcript(url=video_url, lang="en", mode="auto")
                if not getattr(result, "content", None):
                    result = None
                else:
                    logger.info(f"Retrieved English transcript for video {video_id} via Supadata Key #{key_num}.")
            except Exception as en_err:
                if _is_retryable_error(en_err):
                    # The key itself is dead/limited — propagate to the rotation path
                    # instead of treating it as "no English captions" and burning
                    # fallback calls on the same dead key.
                    raise
                logger.debug(
                    f"English transcript not available for {video_id} ({en_err}), falling back to default language..."
                )
                last_error = en_err
                result = None

            # Fallback: try native/auto modes, then the raw YouTube endpoint.
            # Empty results are treated as a miss so the next mode still gets a chance.
            if not result:
                for mode in ("native", "auto"):
                    try:
                        candidate = client.transcript(url=video_url, mode=mode)
                    except Exception as mode_err:
                        if _is_retryable_error(mode_err):
                            raise
                        logger.debug(f"Supadata {mode} mode with key #{key_num} failed: {mode_err}")
                        last_error = mode_err
                        continue
                    if getattr(candidate, "content", None):
                        result = candidate
                        break

            if not result:
                try:
                    candidate = client.youtube.transcript(video_id=video_id)
                except Exception as yt_err:
                    if _is_retryable_error(yt_err):
                        raise
                    logger.debug(f"Supadata YouTube endpoint with key #{key_num} failed: {yt_err}")
                    last_error = yt_err
                    candidate = None
                if getattr(candidate, "content", None):
                    result = candidate

            content = getattr(result, "content", None)
            if not content:
                # Preserve the original API error when every fallback failed, so callers
                # can distinguish "no captions" from a generic empty-response failure.
                if last_error is not None:
                    raise last_error
                raise Exception("Empty transcript content returned.")

            segments = [
                {
                    "text": getattr(chunk, "text", str(chunk)).strip(),
                    "start": round(float(getattr(chunk, "offset", 0) or 0) / 1000, 2),
                    "duration": round(float(getattr(chunk, "duration", 0) or 0) / 1000, 2),
                }
                for chunk in content
                if getattr(chunk, "text", str(chunk)).strip()
            ]

            if not segments:
                raise Exception("No transcript segments found in response.")

            full_text = " ".join(seg["text"] for seg in segments)

            # Successfully extracted! Update active key index to this successful key
            with _active_key_lock:
                _active_key_index = current_idx
            logger.info(
                f"Successfully extracted transcript via Supadata (Key #{key_num} of {num_keys}) "
                f"for {video_id} ({len(segments)} segments)."
            )
            return full_text, segments

        except SupadataError as error:
            if not _is_retryable_error(error):
                logger.error(f"Supadata encountered non-retryable error: {error}")
                raise
            err_msg = getattr(error, "message", str(error))
            logger.warning(
                f"Supadata Key #{key_num} of {num_keys} exhausted or failed: {err_msg}. "
                f"Auto-switching to next available key..."
            )
            attempts.append(f"Key #{key_num}: {err_msg}")
            with _active_key_lock:
                _active_key_index = (current_idx + 1) % num_keys

        except Exception as error:
            if _is_retryable_error(error):
                logger.warning(
                    f"Supadata Key #{key_num} of {num_keys} encountered quota/auth error: {error}. "
                    f"Auto-switching to next available key..."
                )
                attempts.append(f"Key #{key_num}: {str(error)}")
                with _active_key_lock:
                    _active_key_index = (current_idx + 1) % num_keys
            else:
                logger.error(f"Supadata encountered non-retryable error: {error}")
                raise

    # All keys failed
    detail = " | ".join(attempts)
    raise Exception(f"All {num_keys} Supadata API keys were tried and failed for video '{video_id}'. Details: {detail}")


def fetch_transcript(video_id: str) -> Tuple[str, List[Dict[str, Any]]]:
    """Fetch YouTube video transcript via Supadata with multi-key auto-failover."""
    return fetch_from_supadata(video_id)
