import logging
from functools import lru_cache
from langchain_google_genai import ChatGoogleGenerativeAI
from backend.config import (
    GOOGLE_API_KEYS,
    GOOGLE_MODEL,
    GOOGLE_SUMMARY_MODEL,
    GOOGLE_MAX_RETRIES,
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


def _create_genai_client(model_name: str, api_key: str, key_index: int, total_keys: int):
    """Instantiate a ChatGoogleGenerativeAI instance with retry support and failure logging."""
    kwargs = {}
    if "flash-lite" not in model_name.lower():
        kwargs["temperature"] = LLM_TEMPERATURE

    model = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        max_retries=GOOGLE_MAX_RETRIES,
        **kwargs,
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
                f"Google GenAI request failed on API key #{key_index} ({masked_key}): {err_line}. "
                f"Falling back to API key #{key_index + 1}..."
            )
        else:
            logger.error(
                f"Google GenAI request failed on final API key #{key_index} ({masked_key}): {err_line}. "
                "No more fallback keys available."
            )

    return model.with_listeners(on_error=on_error)


def _build_model_with_fallbacks(model_name: str):
    """Build primary ChatGoogleGenerativeAI runnable chained with fallback models across all configured keys."""
    keys = GOOGLE_API_KEYS or [""]
    total_keys = len(keys)
    logger.info(f"Initialized Google GenAI model '{model_name}' with {total_keys} API key(s) for fallback support.")

    models = [_create_genai_client(model_name, key, idx + 1, total_keys) for idx, key in enumerate(keys)]

    if len(models) == 1:
        return models[0]

    return models[0].with_fallbacks(models[1:])


@lru_cache(maxsize=1)
def load_llm():
    """Load ChatGoogleGenerativeAI for chatting and RAG with multi-key fallback."""
    return _build_model_with_fallbacks(GOOGLE_MODEL)


@lru_cache(maxsize=1)
def load_summary_llm():
    """Load ChatGoogleGenerativeAI for video summaries with multi-key fallback."""
    return _build_model_with_fallbacks(GOOGLE_SUMMARY_MODEL)
