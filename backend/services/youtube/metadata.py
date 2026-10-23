import logging

import requests
from typing import Dict, Any

logger = logging.getLogger(__name__)


def get_video_metadata(video_id: str) -> Dict[str, Any]:
    """Fetch video metadata using YouTube's public oEmbed API without requiring an API key."""
    fallback = {
        "title": f"Video ({video_id})",
        "author": "Unknown",
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
    }

    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "title": data.get("title", fallback["title"]),
                "author": data.get("author_name", fallback["author"]),
                "thumbnail": data.get("thumbnail_url", fallback["thumbnail"]),
            }
    except requests.RequestException as exc:
        logger.warning(f"oEmbed metadata request failed for {video_id}: {exc}")
    except (ValueError, KeyError) as exc:
        logger.warning(f"Invalid oEmbed metadata response for {video_id}: {exc}")

    return fallback
