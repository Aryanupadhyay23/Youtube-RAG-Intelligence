from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

class ChunkSummary(BaseModel):
    summary: str = Field(description="Factual summary of the chunk")

class SectionSummary(BaseModel):
    title: str = Field(description="Topic title")
    summary: str = Field(description="Combined summary of the section")
    start_time: int = Field(description="Start time in seconds")
    end_time: int = Field(description="End time in seconds")

CHUNK_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a transcription summarizer.
Your task is to create a concise factual summary of ONLY the provided transcript chunk.

RULES:
- Do not add information.
- Preserve important technical concepts, names, terminology, numbers, and examples.
- Remove filler and repetition.
- Do not refer to the chunk as "this chunk".
- Write a useful standalone summary."""),
    ("human", """Transcript chunk:
{chunk}

Timestamp: {timestamp}

Please summarize this chunk.""")
])

SECTION_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a section summarizer.
Your task is to identify the main topic being discussed across this group of chunk summaries.

RULES:
- Combine related information and remove repeated points.
- Preserve important technical details and do not introduce new facts.
- Maintain logical order.
- Keep timestamps associated with the appropriate topic."""),
    ("human", """Chunk summaries:
{chunk_summaries}

Timestamps: {timestamps}

Please summarize this section.""")
])

FINAL_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert video summarizer.
Produce a complete, comprehensive video summary based ONLY on the provided section summaries.

OUTPUT STRUCTURE:
## Overview
[Concise overview of the video]

## Key Topics
### [Topic 1]
[Details]

### [Topic 2]
[Details]

## Key Takeaways
- [Key point 1]
- [Key point 2]
- [Key point 3]

RULES:
- Base the summary only on the provided section summaries.
- Do not introduce external information or hallucinate facts.
- Preserve the video's logical progression.
- Avoid repeating the same idea.
- Prefer useful information over generic statements."""),
    ("human", """Here is the transcript content from the video:

{section_summaries}

Please generate the complete video summary following the output structure.""")
])
