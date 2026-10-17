"""Timestamp formatting and YouTube playback link utilities for frontend."""
import re

from backend.utils.timestamp import (
    format_timestamp,
    format_time,
    get_youtube_timestamp_url,
    build_youtube_timestamp_url,
    parse_timestamp_seconds,
)

__all__ = [
    "format_timestamp",
    "format_time",
    "get_youtube_timestamp_url",
    "build_youtube_timestamp_url",
    "parse_timestamp_seconds",
    "linkify_timestamps",
]


def linkify_timestamps(text: str, video_id: str) -> str:
    """
    Detect timestamp citations in markdown text (e.g. [03:45], [01:22:15], [08:32 - 08:45])
    and convert them into clickable YouTube playback links.
    """
    if not text or not video_id:
        return text

    def replace_bracketed(match):
        full_match = match.group(0)
        label = full_match.strip("[]")
        start_ts = match.group(1)
        end_idx = match.end()
        # Avoid double-linking if already formatted as markdown link
        if end_idx < len(text) and text[end_idx] == "(":
            return full_match
        sec = parse_timestamp_seconds(start_ts)
        url = get_youtube_timestamp_url(video_id, sec)
        return f"[{label}]({url})"

    pattern_bracketed = r"\[(\d{1,2}:\d{2}(?::\d{2})?)(?:\s*[-–]\s*\d{1,2}:\d{2}(?::\d{2})?)?\]"
    return re.sub(pattern_bracketed, replace_bracketed, text)
