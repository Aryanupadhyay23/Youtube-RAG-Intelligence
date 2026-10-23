from pydantic import BaseModel, Field
from backend.routes.chat.schemas import CHAT_ID_REGEX
from backend.utils.youtube import VIDEO_ID_REGEX


class CreateChatRequest(BaseModel):
    video_id: str = Field(..., pattern=VIDEO_ID_REGEX, description="YouTube 11-character video ID")
    chat_id: str = Field(..., min_length=6, max_length=64, pattern=CHAT_ID_REGEX)
    title: str = Field("New Chat", max_length=200)
    username: str = "default"


class AddMessageRequest(BaseModel):
    video_id: str = Field(..., pattern=VIDEO_ID_REGEX, description="YouTube 11-character video ID")
    user: str = Field(..., min_length=1, max_length=20_000)
    ai: str = Field(..., max_length=40_000)
    username: str = "default"
