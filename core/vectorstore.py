from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)

from langchain_community.vectorstores import FAISS

from core.embeddings import load_embeddings


CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def build_vector_store(transcript_text: str):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    documents = splitter.create_documents(
        [transcript_text]
    )

    embeddings = load_embeddings()

    vector_store = FAISS.from_documents(
        documents,
        embeddings,
    )

    return vector_store