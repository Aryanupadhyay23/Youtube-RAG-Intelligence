from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)

from langchain_core.prompts import (
    PromptTemplate,
)

from langchain_core.output_parsers import (
    StrOutputParser,
)

from core.prompts import (
    SUMMARY_PROMPT,
    MAP_SUMMARY_PROMPT,
    REDUCE_SUMMARY_PROMPT,
)

from utils.constants import (
    SUMMARY_CHUNK_SIZE,
    SUMMARY_CHUNK_OVERLAP,
)


def generate_summary(
    transcript_text,
    llm,
):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=SUMMARY_CHUNK_SIZE,
        chunk_overlap=SUMMARY_CHUNK_OVERLAP,
    )

    chunks = splitter.split_text(transcript_text)

    if len(chunks) == 1:

        prompt = PromptTemplate(
            input_variables=["transcript"],
            template=SUMMARY_PROMPT,
        )

        chain = (
            prompt
            | llm
            | StrOutputParser()
        )

        return chain.invoke({
            "transcript": chunks[0]
        })

    map_prompt = PromptTemplate(
        input_variables=["chunk"],
        template=MAP_SUMMARY_PROMPT,
    )

    map_chain = (
        map_prompt
        | llm
        | StrOutputParser()
    )

    partial_summaries = []

    for chunk in chunks:

        summary = map_chain.invoke({
            "chunk": chunk
        })

        partial_summaries.append(summary)

    reduce_prompt = PromptTemplate(
        input_variables=["summaries"],
        template=REDUCE_SUMMARY_PROMPT,
    )

    reduce_chain = (
        reduce_prompt
        | llm
        | StrOutputParser()
    )

    final_summary = reduce_chain.invoke({
        "summaries": "\n\n".join(partial_summaries)
    })

    return final_summary