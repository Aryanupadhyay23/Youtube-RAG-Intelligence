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
    ("system", """ROLE
You are a transcription summarizer.

TASK
Create a concise factual summary of ONLY this chunk.

INPUTS
Transcript chunk: {chunk}
Timestamp: {timestamp}

RULES
- Do not add information.
- Preserve important technical concepts.
- Remove filler and repetition.
- Preserve important names, terminology, numbers, and examples.
- Do not interpret beyond the text.
- Do not refer to the chunk as "this chunk".
- Write a useful standalone summary.
""")
])

SECTION_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """ROLE
You are a section summarizer.

TASK
Identify the main topic being discussed across this group of chunks.

INPUTS
Chunk summaries: {chunk_summaries}
Timestamps: {timestamps}

RULES
- Combine related information.
- Remove repeated points.
- Preserve important technical details.
- Do not introduce new facts.
- Maintain logical order.
- Keep timestamps associated with the appropriate topic.
""")
])

FINAL_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """ROLE
You are a video summarizer.

TASK
Produce the complete video summary based ONLY on the provided section summaries.

OUTPUT STRUCTURE:
## Overview
[Short overview]

## Key Topics
### [Topic 1]
...

## Key Takeaways
- ...

RULES
- Base the summary only on the provided section summaries.
- Do not introduce external information.
- Do not hallucinate missing sections.
- Preserve the video's logical progression.
- Avoid repeating the same idea.
- Prefer useful information over generic statements.

INPUTS:
{section_summaries}
""")
])
