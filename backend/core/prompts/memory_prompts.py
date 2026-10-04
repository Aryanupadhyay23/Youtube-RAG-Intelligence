from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

class MemoryUpdateResult(BaseModel):
    updated_memory: str = Field(description="The updated compact conversational memory")

MEMORY_UPDATE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """ROLE
You are a conversational memory manager.

TASK
Summarize the conversation to maintain context for future interactions.

INPUTS
Existing conversation summary: {existing_summary}
New messages: {new_messages}

RULES
- Create a compact factual summary of what the user has asked, what has been discussed, and any important unresolved context.
- Keep it compact.
- Do not store the entire transcript.
- Do not store irrelevant conversational filler.
- Do not infer user preferences unless explicitly stated.
- Only store information that is useful for continuing the conversation (e.g. "The user is currently asking about X").
""")
])
