from pydantic import BaseModel


class SummaryRequest(BaseModel):
    transcript_text: str
