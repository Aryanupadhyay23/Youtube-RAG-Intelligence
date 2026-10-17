from functools import lru_cache
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from backend.config import GOOGLE_API_KEY
from backend.utils.constants import EMBEDDING_MODEL


@lru_cache(maxsize=1)
def load_embeddings():
    """Load and cache the Google Gemini Embedding model."""
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )
