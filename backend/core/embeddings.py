from langchain_google_genai import GoogleGenerativeAIEmbeddings
from backend.config import GOOGLE_API_KEY
from backend.utils.constants import EMBEDDING_MODEL


def load_embeddings():
    """Load Google Gemini Embedding model."""
    return GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL,
        google_api_key=GOOGLE_API_KEY,
    )
