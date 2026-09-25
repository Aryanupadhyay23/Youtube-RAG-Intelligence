from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field

class RewriteResult(BaseModel):
    standalone_query: str = Field(description="The rewritten standalone query")
    needs_rewrite: bool = Field(description="Whether the query actually needed rewriting")

class CorrectResult(BaseModel):
    corrected_query: str = Field(description="The new, corrected search query")

# 1. Query Rewrite Prompt
REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """ROLE
You are a query optimization assistant for a YouTube RAG system.

TASK
Convert a conversational/follow-up question into a standalone retrieval query.

RULES
- Preserve the user's actual intent.
- Do not answer the question.
- Do not add facts that are not present in the conversation.
- Do not invent entities.
- Do not make the query unnecessarily long.
- Remove conversational references such as "it", "they", "that", "this".
- Preserve important technical terminology.
- Optimize for retrieval, not natural conversation.
- If the question is already standalone (e.g. "What is RAG?"), return it unchanged.
"""),
    MessagesPlaceholder("chat_history"),
    ("user", "{question}")
])

# 2. Corrective Query Prompt
CORRECTIVE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """ROLE
You are a search correction assistant.

TASK
The previous search query returned poor results. Create a better retrieval query to search the video transcript again.

INPUTS
Original user query: {original_query}
Failed search query: {failed_query}

RULES
- Identify what information the current query is missing.
- Make implicit references explicit.
- Add useful terminology from the conversation.
- Remove ambiguity.
- Preserve the original intent.
- Do not invent facts.
- Do not add information from outside the provided conversation.
- Keep the corrected query concise.
- DO NOT answer the user's question, only improve the search query.
"""),
    MessagesPlaceholder("chat_history"),
    ("user", "Rewrite search query for: {original_query}")
])
