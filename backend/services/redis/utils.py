from typing import Optional

SESSION_KEY_PREFIX = "yt_rag:video"
CHAT_KEY_PREFIX = "yt_rag:chat"
USER_KEY_PREFIX = "yt_rag:user"
DEFAULT_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days retention


def clean_username(username: Optional[str]) -> str:
    """Normalize and sanitize username, defaulting to 'default'."""
    if not username:
        return "default"
    u = username.strip().lower()
    cleaned = "".join(c for c in u if c.isalnum() or c in ("_", "-"))
    if not cleaned or cleaned in ("guest", "none", "null"):
        return "default"
    return cleaned
