from pydantic import BaseModel, Field


class SummaryRequest(BaseModel):
    transcript_text: str = Field(
        ..., max_length=500_000, description="Full video transcript text, capped at 500k characters"
    )
