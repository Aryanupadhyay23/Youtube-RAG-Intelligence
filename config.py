import os

from dotenv import load_dotenv

from utils.constants import (
    APP_TITLE,
    APP_CAPTION,
    MEMORY_WINDOW,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    SUMMARY_CHUNK_SIZE,
    SUMMARY_CHUNK_OVERLAP,
    RETRIEVER_K,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    EMBEDDING_MODEL,
    QUICK_QUESTIONS,
)


# ── Environment Detection ─────────────────────────────────────────────────────

IS_HUGGINGFACE = os.environ.get("SPACE_ID") is not None


# ── Load Environment Variables ────────────────────────────────────────────────

if not IS_HUGGINGFACE:
    load_dotenv(override=False)


# ── API Keys ──────────────────────────────────────────────────────────────────

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

HF_TOKEN = os.environ.get("HF_TOKEN", "")

SUPADATA_KEYS = [
    os.environ.get("SUPADATA_KEY_1"),
    os.environ.get("SUPADATA_KEY_2"),
    os.environ.get("SUPADATA_KEY_3"),
]

SUPADATA_KEYS = [
    key
    for key in SUPADATA_KEYS
    if key
]

if HF_TOKEN:
    os.environ["HF_TOKEN"] = HF_TOKEN