import requests
from typing import Dict, Any
from frontend.services.api.common import API_BASE_URL


def initialize_video(
    video_id: str,
    transcript_segments: list = None,
    transcript_text: str = "",
) -> Dict[str, Any]:
    """Call backend /init to fetch transcript & metadata and build hybrid vector stores."""
    payload = {
        "video_id": video_id,
    }
    r = requests.post(f"{API_BASE_URL}/init", json=payload, timeout=180)
    if r.status_code != 200:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        raise RuntimeError(detail)
    return r.json()


def reset_backend_video(video_id: str = ""):
    """Notify backend to evict the in-memory vector store and immediately free RAM."""
    try:
        requests.post(f"{API_BASE_URL}/reset?video_id={video_id}", timeout=5)
    except Exception:
        pass
