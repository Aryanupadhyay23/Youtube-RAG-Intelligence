from pydantic import BaseModel, Field
from backend.utils.youtube import VIDEO_ID_REGEX


class InitRequest(BaseModel):
    video_id: str = Field(..., pattern=VIDEO_ID_REGEX, description="YouTube 11-character video ID")
