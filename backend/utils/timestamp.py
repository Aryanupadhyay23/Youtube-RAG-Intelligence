def format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    seconds = max(0, int(seconds))
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
    """Convert HH:MM:SS or MM:SS string into integer seconds.

    Numeric single-part values are treated as seconds. Returns 0 for
    malformed input instead of raising.
    """
    try:
        parts = ts.strip("[]").split(":")
        ints = [int(p.strip()) for p in parts if p.strip()]
    except (ValueError, AttributeError):
        return 0
    if len(ints) == 3:
        return ints[0] * 3600 + ints[1] * 60 + ints[2]
    if len(ints) == 2:
        return ints[0] * 60 + ints[1]
    if len(ints) == 1:
        return max(0, ints[0])
    return 0
