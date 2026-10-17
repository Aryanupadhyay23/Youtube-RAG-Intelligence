from typing import List, Dict, Any
from pydantic import BaseModel


class InitRequest(BaseModel):
    video_id: str
    transcript_text: str = ""
    transcript_segments: List[Dict[str, Any]] = []
