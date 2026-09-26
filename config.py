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
    SEMANTIC_TOP_K,
    BM25_TOP_K,
    FINAL_TOP_K,
    RRF_K,
    MAX_RETRIEVAL_ATTEMPTS,
    RECENT_MESSAGE_COUNT,
    LLM_MODEL,
    SUMMARY_MODEL,
    LLM_TEMPERATURE,
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
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")

HF_TOKEN = os.environ.get("HF_TOKEN", "")

SUPADATA_KEYS = [
    os.environ.get("SUPADATA_KEY_1") or os.environ.get("SUPADATA_KEY_ONE"),
    os.environ.get("SUPADATA_KEY_2") or os.environ.get("SUPADATA_KEY_TWO"),
    os.environ.get("SUPADATA_KEY_3") or os.environ.get("SUPADATA_KEY_THREE"),
    os.environ.get("SUPADATA_KEY_4") or os.environ.get("SUPADATA_KEY_FOUR"),
]

SUPADATA_KEYS = [
    key
    for key in SUPADATA_KEYS
    if key
]

TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")

OLLAMA_API_KEY = os.environ.get("OLLAMA") or os.environ.get("OLLAMA_API_KEY", "")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST") or os.environ.get("OLLAMA_BASE_URL", "https://ollama.com")

if OLLAMA_API_KEY:
    os.environ["OLLAMA_API_KEY"] = OLLAMA_API_KEY
if OLLAMA_HOST:
    os.environ["OLLAMA_HOST"] = OLLAMA_HOST

if HF_TOKEN:
    os.environ["HF_TOKEN"] = HF_TOKEN