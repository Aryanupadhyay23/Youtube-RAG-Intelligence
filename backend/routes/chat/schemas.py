from typing import List, Dict
from pydantic import BaseModel, Field

VIDEO_ID_REGEX = r"^[A-Za-z0-9_-]{11}$"


class ChatRequest(BaseModel):
    video_id: str = Field(..., pattern=VIDEO_ID_REGEX, description="YouTube 11-character video ID")
    chat_id: str
    query: str
    chat_history: List[Dict[str, str]] = []
    username: str = "default"
