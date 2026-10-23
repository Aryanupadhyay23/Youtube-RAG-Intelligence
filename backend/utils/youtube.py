"""Shared YouTube video ID validation and URL parsing utilities."""

import re
from typing import Optional

# Pydantic pattern for a standard 11-character YouTube video ID.
VIDEO_ID_REGEX = r"^[A-Za-z0-9_-]{11}$"

_VIDEO_ID_PATTERNS = (
    r"(?:v=|vi=|youtu\.be/|(?:embed|shorts|live|v)/)([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])",
    r"^([A-Za-z0-9_-]{11})$",
)


def extract_video_id(url: str) -> Optional[str]:
    """Extract a standard 11-character YouTube ID from a URL or raw ID.

    The capture group is bounded by a negative lookahead so that longer valid
    character runs (malformed/garbage URLs) cause a lookup miss instead of
    silently truncating to the first 11 characters.
    """
    if not url:
        return None

    for pattern in _VIDEO_ID_PATTERNS:
        match = re.search(pattern, url.strip())
        if match:
            return match.group(1)
    return None
