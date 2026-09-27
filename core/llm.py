import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

from utils.constants import (
    LLM_MODEL,
    SUMMARY_MODEL,
    LLM_TEMPERATURE,
)

load_dotenv()


def load_llm():
    """Load the primary LLM (Groq) for normal chat and RAG flow."""
    return ChatGroq(
        model=LLM_MODEL,
        groq_api_key=os.environ.get("GROQ_API_KEY"),
        temperature=LLM_TEMPERATURE,
    )


def load_summary_llm():
    """Load the summarization LLM via Ollama."""
    ollama_host = (
        os.environ.get("OLLAMA_HOST")
        or os.environ.get("OLLAMA_BASE_URL")
        or "https://ollama.com"
    )
    ollama_key = (
        os.environ.get("OLLAMA_API_KEY")
        or os.environ.get("OLLAMA")
    )

    client_kwargs = {"headers": {"Authorization": f"Bearer {ollama_key}"}} if ollama_key else {}

    return ChatOllama(
        model=SUMMARY_MODEL,
        base_url=ollama_host,
        temperature=LLM_TEMPERATURE,
        client_kwargs=client_kwargs,
    )