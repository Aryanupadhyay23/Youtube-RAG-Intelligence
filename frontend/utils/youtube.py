"""YouTube URL parsing utilities for frontend."""
import re


def extract_video_id(url: str):
    """Extract standard 11-char YouTube ID from various URL formats or raw ID."""
    if not url:
        return None
    patterns = [
        r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url.strip())
        if match:
            return match.group(1)
    return None
