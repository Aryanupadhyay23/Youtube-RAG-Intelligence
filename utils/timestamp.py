def format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def get_youtube_timestamp_url(video_id: str, seconds: float) -> str:
    """Return a YouTube URL with a specific timestamp."""
    return f"https://youtube.com/watch?v={video_id}&t={int(seconds)}s"
