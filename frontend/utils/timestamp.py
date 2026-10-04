"""Timestamp formatting and YouTube playback link utilities for frontend."""
import re


def format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


# Backwards-compatible alias
format_time = format_timestamp


def get_youtube_timestamp_url(video_id: str, seconds: float) -> str:
    """Return a YouTube URL with a specific playback timestamp."""
    return f"https://youtube.com/watch?v={video_id}&t={int(seconds)}s"


# Backwards-compatible alias
build_youtube_timestamp_url = get_youtube_timestamp_url


def parse_timestamp_seconds(ts: str) -> int:
    """Convert HH:MM:SS or MM:SS string into integer seconds."""
    parts = [int(p) for p in ts.strip("[]").split(":")]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return 0


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
        start_idx = match.start()
        end_idx = match.end()
        # Avoid double-linking if already formatted as markdown link
        if end_idx < len(text) and text[end_idx] == "(":
            return full_match
        sec = parse_timestamp_seconds(start_ts)
        url = get_youtube_timestamp_url(video_id, sec)
        return f"[{label}]({url})"

    pattern_bracketed = r"\[(\d{1,2}:\d{2}(?::\d{2})?)(?:\s*[-–]\s*\d{1,2}:\d{2}(?::\d{2})?)?\]"
    return re.sub(pattern_bracketed, replace_bracketed, text)
