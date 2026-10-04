import logging
from functools import lru_cache
from langchain_ollama import ChatOllama
from backend.config import (
    OLLAMA_HOST,
    OLLAMA_API_KEYS,
    OLLAMA_API_KEY,
    OLLAMA_SUMMARY_MODEL,
    OLLAMA_MODEL,
)
from backend.utils.constants import LLM_TEMPERATURE

logger = logging.getLogger(__name__)


def _mask_api_key(key: str) -> str:
    """Mask key for secure logging."""
    if not key:
        return "None"
    if len(key) <= 8:
        return "***"
    return f"{key[:6]}...{key[-4:]}"


def _create_ollama_client(model_name: str, api_key: str, key_index: int, total_keys: int):
    """Instantiate a ChatOllama instance with Authorization header and failure logging."""
    client_kwargs = (
        {"headers": {"Authorization": f"Bearer {api_key}"}}
        if api_key
        else {}
    )
    model = ChatOllama(
        model=model_name,
        base_url=OLLAMA_HOST,
        temperature=LLM_TEMPERATURE,
        client_kwargs=client_kwargs,
    )

    def on_error(run):
        err_msg = getattr(run, "error", "")
        if isinstance(err_msg, str) and "\n" in err_msg:
            err_line = err_msg.strip().splitlines()[-1]
        else:
            err_line = str(err_msg)

        masked_key = _mask_api_key(api_key)
        if key_index < total_keys:
            logger.warning(
                f"Ollama request failed on API key #{key_index} ({masked_key}): {err_line}. "
                f"Falling back to API key #{key_index + 1}..."
            )
        else:
            logger.error(
                f"Ollama request failed on final API key #{key_index} ({masked_key}): {err_line}. "
                "No more fallback keys available."
            )

    return model.with_listeners(on_error=on_error)


def _build_model_with_fallbacks(model_name: str):
    """Build primary ChatOllama runnable chained with fallback models across all configured keys."""
    keys = OLLAMA_API_KEYS if OLLAMA_API_KEYS else ([OLLAMA_API_KEY] if OLLAMA_API_KEY else [""])
    total_keys = len(keys)
    logger.info(f"Initialized Ollama model '{model_name}' with {total_keys} API key(s) for fallback support.")

    models = [
        _create_ollama_client(model_name, key, idx + 1, total_keys)
        for idx, key in enumerate(keys)
    ]

    if len(models) == 1:
        return models[0]

    return models[0].with_fallbacks(models[1:])


@lru_cache(maxsize=1)
def load_llm():
    """Load ChatOllama for chatting and RAG with multi-key fallback."""
    return _build_model_with_fallbacks(OLLAMA_MODEL)


@lru_cache(maxsize=1)
def load_summary_llm():
    """Load ChatOllama for video summaries with multi-key fallback."""
    return _build_model_with_fallbacks(OLLAMA_SUMMARY_MODEL)

