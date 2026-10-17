from pydantic import BaseModel


class CreateChatRequest(BaseModel):
    video_id: str
    chat_id: str
    title: str = "New Chat"
    username: str = "default"


class AddMessageRequest(BaseModel):
    video_id: str
    user: str
    ai: str
    username: str = "default"
