import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from config import EMBEDDING_MODEL


def load_embeddings():
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=api_key,
    )