from pydantic import BaseModel, Field

VIDEO_ID_REGEX = r"^[A-Za-z0-9_-]{11}$"


class CreateChatRequest(BaseModel):
    video_id: str = Field(..., pattern=VIDEO_ID_REGEX, description="YouTube 11-character video ID")
    chat_id: str
    title: str = "New Chat"
    username: str = "default"


class AddMessageRequest(BaseModel):
    video_id: str = Field(..., pattern=VIDEO_ID_REGEX, description="YouTube 11-character video ID")
    user: str
    ai: str
    username: str = "default"
