import requests
from typing import Dict, Any


def get_video_metadata(video_id: str) -> Dict[str, Any]:
    """Fetch video metadata using YouTube's public oEmbed API without requiring an API key."""
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            return {
                "title": data.get("title", "YouTube Video"),
                "author": data.get("author_name", "YouTube Channel"),
                "thumbnail": data.get("thumbnail_url", f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"),
            }
    except Exception:
        pass

    return {
        "title": "YouTube Video",
        "author": "YouTube Channel",
        "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
    }
