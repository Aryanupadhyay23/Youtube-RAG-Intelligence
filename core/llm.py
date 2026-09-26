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


def get_groq_api_key():
    return os.environ.get("GROQ_API_KEY")


def load_llm():
    """Load the primary LLM (Groq) for normal chat and RAG flow."""
    groq_api_key = get_groq_api_key()
    return ChatGroq(
        model=LLM_MODEL,
        groq_api_key=groq_api_key,
        temperature=LLM_TEMPERATURE,
    )


def load_summary_llm():
    """Load the summarization LLM (gpt-oss:120b-cloud via Ollama)."""
    ollama_key = (
        os.environ.get("OLLAMA")
        or os.environ.get("OLLAMA_API_KEY")
    )
    ollama_host = (
        os.environ.get("OLLAMA_HOST")
        or os.environ.get("OLLAMA_BASE_URL")
        or "https://ollama.com"
    )

    if ollama_key:
        os.environ["OLLAMA_API_KEY"] = ollama_key
    if ollama_host:
        os.environ["OLLAMA_HOST"] = ollama_host

    client_kwargs = {}
    if ollama_key:
        client_kwargs["headers"] = {"Authorization": f"Bearer {ollama_key}"}

    kwargs = {
        "model": SUMMARY_MODEL,
        "base_url": ollama_host,
        "temperature": LLM_TEMPERATURE,
    }
    if client_kwargs:
        kwargs["client_kwargs"] = client_kwargs
        kwargs["async_client_kwargs"] = client_kwargs

    return ChatOllama(**kwargs)