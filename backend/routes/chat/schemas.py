from typing import List
from pydantic import BaseModel, Field
from backend.utils.youtube import VIDEO_ID_REGEX

CHAT_ID_REGEX = r"^[A-Za-z0-9_-]+$"


class ChatTurn(BaseModel):
    """A single stored conversational turn. Keys are enforced to match the
    `{"user": ..., "ai": ...}` shape the workflow expects."""

    user: str
    ai: str


class ChatRequest(BaseModel):
    video_id: str = Field(..., pattern=VIDEO_ID_REGEX, description="YouTube 11-character video ID")
    chat_id: str = Field(..., min_length=6, max_length=64, pattern=CHAT_ID_REGEX)
    query: str = Field(..., min_length=1, max_length=20_000)
    chat_history: List[ChatTurn] = []
    username: str = "default"
