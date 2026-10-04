import re
import json
import urllib.request
from backend.utils.timestamp import get_youtube_timestamp_url, build_youtube_timestamp_url


def extract_video_id(url: str):
    """Extract standard 11-char YouTube ID from various URL formats or raw ID."""
    patterns = [
        r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url.strip())
        if match:
            return match.group(1)
    return None


def get_video_metadata(video_id: str) -> dict:
    """Fetch video metadata using YouTube's public oEmbed API without requiring an API key."""
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read())

        return {
            "title": data.get("title", "Unknown Title"),
            "author": data.get("author_name", "Unknown Channel"),
            "thumbnail": data.get("thumbnail_url", ""),
        }
    except Exception:
        return {
            "title": "Unknown Title",
            "author": "Unknown Channel",
            "thumbnail": "",
        }
