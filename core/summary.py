from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)

from langchain_core.output_parsers import (
    StrOutputParser,
)

from core.prompts import (
    CHUNK_SUMMARY_PROMPT,
    FINAL_SUMMARY_PROMPT,
)

from utils.constants import (
    SUMMARY_CHUNK_SIZE,
    SUMMARY_CHUNK_OVERLAP,
)


from core.llm import load_summary_llm


def generate_summary(
    transcript_text,
    llm=None,
):
    if llm is None:
        llm = load_summary_llm()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=SUMMARY_CHUNK_SIZE,
        chunk_overlap=SUMMARY_CHUNK_OVERLAP,
    )

    chunks = splitter.split_text(transcript_text)

    if len(chunks) == 1:

        chain = (
            FINAL_SUMMARY_PROMPT
            | llm
            | StrOutputParser()
        )

        return chain.invoke({
            "section_summaries": chunks[0]
        })

    map_chain = (
        CHUNK_SUMMARY_PROMPT
        | llm
        | StrOutputParser()
    )

    partial_summaries = []

    for chunk in chunks:

        summary = map_chain.invoke({
            "chunk": chunk,
            "timestamp": "N/A"
        })

        partial_summaries.append(summary)

    reduce_chain = (
        FINAL_SUMMARY_PROMPT
        | llm
        | StrOutputParser()
    )

    final_summary = reduce_chain.invoke({
        "section_summaries": "\n\n".join(partial_summaries)
    })

    return final_summary