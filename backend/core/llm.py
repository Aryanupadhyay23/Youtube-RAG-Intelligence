import os
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from backend.config import GROQ_API_KEY, OLLAMA_HOST, OLLAMA_API_KEY
from backend.utils.constants import LLM_MODEL, SUMMARY_MODEL, LLM_TEMPERATURE


def load_llm():
    """Load the primary LLM (Groq) for chat and RAG flow."""
    return ChatGroq(
        model=LLM_MODEL,
        groq_api_key=GROQ_API_KEY,
        temperature=LLM_TEMPERATURE,
    )


def load_summary_llm():
    """Load the summarization LLM via Ollama."""
    client_kwargs = {"headers": {"Authorization": f"Bearer {OLLAMA_API_KEY}"}} if OLLAMA_API_KEY else {}

    return ChatOllama(
        model=SUMMARY_MODEL,
        base_url=OLLAMA_HOST,
        temperature=LLM_TEMPERATURE,
        client_kwargs=client_kwargs,
    )
