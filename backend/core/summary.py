from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.output_parsers import StrOutputParser

from backend.core.prompts import CHUNK_SUMMARY_PROMPT, FINAL_SUMMARY_PROMPT
from backend.utils.constants import SUMMARY_CHUNK_SIZE, SUMMARY_CHUNK_OVERLAP
from backend.core.llm import load_summary_llm


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
        chain = FINAL_SUMMARY_PROMPT | llm | StrOutputParser()
        return chain.invoke({"section_summaries": chunks[0]})

    map_chain = CHUNK_SUMMARY_PROMPT | llm | StrOutputParser()
    partial_summaries = [map_chain.invoke({"chunk": chunk}) for chunk in chunks]

    reduce_chain = FINAL_SUMMARY_PROMPT | llm | StrOutputParser()
    return reduce_chain.invoke({"section_summaries": "\n\n".join(partial_summaries)})
