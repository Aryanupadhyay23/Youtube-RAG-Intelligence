from typing import List, Dict
from pydantic import BaseModel


class ChatRequest(BaseModel):
    video_id: str
    chat_id: str
    query: str
    chat_history: List[Dict[str, str]] = []
    username: str = "default"
