from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.output_parsers import StrOutputParser

from backend.core.prompts import CHUNK_SUMMARY_PROMPT, FINAL_SUMMARY_PROMPT
from backend.utils.constants import SUMMARY_CHUNK_SIZE, SUMMARY_CHUNK_OVERLAP
from backend.core.llm import load_summary_llm

import logging

logger = logging.getLogger(__name__)


def generate_summary(transcript_text: str, llm=None) -> str:
    """Generate summary using single-pass or map-reduce depending on transcript size."""
    if llm is None:
        llm = load_summary_llm()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=SUMMARY_CHUNK_SIZE,
        chunk_overlap=SUMMARY_CHUNK_OVERLAP,
    )
    chunks = splitter.split_text(transcript_text)

    if len(chunks) == 1:
        # Single-pass: use the final summary prompt directly with the full text
        chain = FINAL_SUMMARY_PROMPT | llm | StrOutputParser()
        return chain.invoke({"section_summaries": chunks[0]})

    # Map phase: summarize each chunk individually
    partial_summaries = []
    for idx, chunk in enumerate(chunks):
        try:
            map_chain = CHUNK_SUMMARY_PROMPT | llm | StrOutputParser()
            # Pass timestamp placeholder since we don't have per-chunk timestamps
            # when called from the /summary endpoint with raw transcript text
            summary = map_chain.invoke({
                "chunk": chunk,
                "timestamp": f"Chunk {idx + 1}/{len(chunks)}",
            })
            partial_summaries.append(summary)
        except Exception as e:
            logger.warning(f"Failed to summarize chunk {idx + 1}: {e}")
            # Use truncated chunk as fallback
            partial_summaries.append(chunk[:500] + "...")

    # Reduce phase: combine all chunk summaries into final summary
    reduce_chain = FINAL_SUMMARY_PROMPT | llm | StrOutputParser()
    return reduce_chain.invoke({"section_summaries": "\n\n".join(partial_summaries)})
