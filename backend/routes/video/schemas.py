from pydantic import BaseModel, Field

VIDEO_ID_REGEX = r"^[A-Za-z0-9_-]{11}$"


class InitRequest(BaseModel):
    video_id: str = Field(..., pattern=VIDEO_ID_REGEX, description="YouTube 11-character video ID")
