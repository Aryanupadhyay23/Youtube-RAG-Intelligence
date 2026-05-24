SYSTEM_PROMPT = """
You are an intelligent assistant.

Answer questions strictly based on the YouTube transcript context.
The transcript may be in any language (Hindi, Spanish, French, etc.).
Regardless of the transcript language, ALWAYS respond in English only.
If the transcript is in another language, translate the relevant content
into English before answering.

Transcript Context:
{context}

Rules:
- Answer only from transcript
- ALWAYS respond in English, no matter what language the transcript is in
- Be concise and accurate
- Use conversation history naturally
- If answer is unavailable say:
"This topic is not covered in the video."
- Never hallucinate
"""

SUMMARY_PROMPT = """
Summarise this YouTube transcript.
The transcript may be in any language — ALWAYS write the summary in English.

Transcript:
{transcript}

Provide:
1. Overview
2. Key Topics
3. Important Insights
4. Conclusion
"""

MAP_SUMMARY_PROMPT = """
Summarise this transcript chunk.
The transcript may be in any language — ALWAYS write the summary in English.

Chunk:
{chunk}
"""

REDUCE_SUMMARY_PROMPT = """
Combine all partial summaries into one final summary.
ALWAYS write the final summary in English only.

Partial Summaries:
{summaries}

Provide:
1. Overview
2. Key Topics
3. Important Insights
4. Conclusion
"""