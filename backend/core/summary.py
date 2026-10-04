import asyncio
import logging
from typing import AsyncGenerator, Dict, Any, List

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.output_parsers import StrOutputParser

from backend.core.prompts import CHUNK_SUMMARY_PROMPT, FINAL_SUMMARY_PROMPT
from backend.utils.constants import SUMMARY_CHUNK_SIZE, SUMMARY_CHUNK_OVERLAP
from backend.core.llm import load_summary_llm

logger = logging.getLogger(__name__)


async def generate_summary_async(
    transcript_text: str,
    llm=None,
    max_concurrency: int = 4,
) -> str:
    """
    Generate summary using single-pass or parallel map-reduce depending on transcript size.
    Uses asyncio.gather with a semaphore to process map chunks concurrently.
    """
    if llm is None:
        llm = load_summary_llm()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=SUMMARY_CHUNK_SIZE,
        chunk_overlap=SUMMARY_CHUNK_OVERLAP,
    )
    chunks = splitter.split_text(transcript_text)

    if not chunks:
        return "No transcript text available to summarize."

    if len(chunks) == 1:
        # Single-pass: use final summary prompt directly
        chain = FINAL_SUMMARY_PROMPT | llm | StrOutputParser()
        return await chain.ainvoke({"section_summaries": chunks[0]})

    # Parallel Map phase with bounded concurrency
    semaphore = asyncio.Semaphore(max_concurrency)

    async def summarize_chunk(idx: int, chunk: str) -> tuple[int, str]:
        async with semaphore:
            try:
                map_chain = CHUNK_SUMMARY_PROMPT | llm | StrOutputParser()
                summary = await map_chain.ainvoke({
                    "chunk": chunk,
                    "timestamp": f"Section {idx + 1}/{len(chunks)}",
                })
                return idx, summary
            except Exception as e:
                logger.warning(f"Failed to summarize chunk {idx + 1}: {e}")
                # Fallback to truncated text
                return idx, chunk[:500] + "..."

    tasks = [summarize_chunk(idx, chunk) for idx, chunk in enumerate(chunks)]
    results = await asyncio.gather(*tasks)
    results.sort(key=lambda x: x[0])
    partial_summaries = [r[1] for r in results]

    # Reduce phase: synthesize full structured summary
    reduce_chain = FINAL_SUMMARY_PROMPT | llm | StrOutputParser()
    return await reduce_chain.ainvoke({"section_summaries": "\n\n".join(partial_summaries)})


async def generate_summary_stream(
    transcript_text: str,
    llm=None,
    max_concurrency: int = 4,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Asynchronous generator streaming real-time status and final tokens for video summarization.
    Yields events:
      {"type": "status", "message": "..."}
      {"type": "token", "token": "..."}
      {"type": "end"}
    """
    if llm is None:
        llm = load_summary_llm()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=SUMMARY_CHUNK_SIZE,
        chunk_overlap=SUMMARY_CHUNK_OVERLAP,
    )
    chunks = splitter.split_text(transcript_text)

    if not chunks:
        yield {"type": "status", "message": "No transcript text found."}
        yield {"type": "end"}
        return

    total_chunks = len(chunks)

    if total_chunks == 1:
        yield {"type": "status", "message": "Generating single-pass summary..."}
        chain = FINAL_SUMMARY_PROMPT | llm | StrOutputParser()
        async for token in chain.astream({"section_summaries": chunks[0]}):
            if token:
                yield {"type": "token", "token": token}
        yield {"type": "end"}
        return

    # Parallel Map phase
    yield {
        "type": "status",
        "message": f"Processing {total_chunks} sections in parallel (concurrency limit: {max_concurrency})...",
    }

    semaphore = asyncio.Semaphore(max_concurrency)
    completed_counter = 0

    async def summarize_chunk_with_progress(idx: int, chunk: str) -> tuple[int, str]:
        nonlocal completed_counter
        async with semaphore:
            try:
                map_chain = CHUNK_SUMMARY_PROMPT | llm | StrOutputParser()
                summary = await map_chain.ainvoke({
                    "chunk": chunk,
                    "timestamp": f"Section {idx + 1}/{total_chunks}",
                })
            except Exception as e:
                logger.warning(f"Chunk {idx + 1} summary failed: {e}")
                summary = chunk[:500] + "..."
            completed_counter += 1
            return idx, summary

    tasks = [summarize_chunk_with_progress(idx, chunk) for idx, chunk in enumerate(chunks)]
    results = await asyncio.gather(*tasks)
    results.sort(key=lambda x: x[0])
    partial_summaries = [r[1] for r in results]

    # Reduce Phase: Stream tokens
    yield {
        "type": "status",
        "message": "Synthesizing executive overview, key topics, and takeaways...",
    }

    reduce_chain = FINAL_SUMMARY_PROMPT | llm | StrOutputParser()
    async for token in reduce_chain.astream({"section_summaries": "\n\n".join(partial_summaries)}):
        if token:
            yield {"type": "token", "token": token}

    yield {"type": "end"}


def generate_summary(transcript_text: str, llm=None) -> str:
    """
    Synchronous entrypoint for backwards compatibility.
    Runs the asynchronous parallel map-reduce workflow.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(generate_summary_async(transcript_text, llm))
        else:
            return asyncio.run(generate_summary_async(transcript_text, llm))
    except Exception:
        # Fallback if loop handling fails
        return asyncio.run(generate_summary_async(transcript_text, llm))
