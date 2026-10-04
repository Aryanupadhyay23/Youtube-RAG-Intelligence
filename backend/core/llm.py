from functools import lru_cache
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama
from backend.config import (
    GROQ_API_KEYS,
    GROQ_MODEL,
    OLLAMA_HOST,
    OLLAMA_API_KEY,
    OLLAMA_SUMMARY_MODEL,
)
from backend.utils.constants import LLM_TEMPERATURE


@lru_cache(maxsize=1)
def load_llm():
    """Load ChatGroq (Qwen 3.8 27B) with multi-key fallback for chatting and RAG."""
    models = [
        ChatGroq(model=GROQ_MODEL, groq_api_key=k, temperature=LLM_TEMPERATURE)
        for k in GROQ_API_KEYS
    ]
    return models[0].with_fallbacks(models[1:]) if len(models) > 1 else models[0]


@lru_cache(maxsize=1)
def load_summary_llm():
    """Load ChatOllama (gpt-oss:20b on Ollama Cloud) for video summaries."""
    client_kwargs = (
        {"headers": {"Authorization": f"Bearer {OLLAMA_API_KEY}"}}
        if OLLAMA_API_KEY
        else {}
    )
    return ChatOllama(
        model=OLLAMA_SUMMARY_MODEL,
        base_url=OLLAMA_HOST,
        temperature=LLM_TEMPERATURE,
        client_kwargs=client_kwargs,
    )

