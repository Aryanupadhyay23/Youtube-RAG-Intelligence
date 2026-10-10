import os
from dotenv import load_dotenv

from backend.utils.constants import *

# Load .env file
load_dotenv(override=True)

def _clean_env(val: str | None) -> str:
    """Strip whitespace and surrounding single/double quotes (often preserved literally by Docker --env-file)."""
    if not val:
        return ""
    val = val.strip()
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        val = val[1:-1].strip()
    return val


# --- Groq Configuration (Qwen 3.8 27B with 3 Fallback Keys) ---
GROQ_API_KEYS = [
    cleaned for key in [
        os.environ.get("GROQ_API_KEY_1"),
        os.environ.get("GROQ_API_KEY_2"),
        os.environ.get("GROQ_API_KEY_3"),
        os.environ.get("GROQ_API_KEY"),
    ]
    if (cleaned := _clean_env(key))
]
GROQ_MODEL = _clean_env(os.environ.get("GROQ_MODEL")) or LLM_MODEL

GOOGLE_API_KEY = _clean_env(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
TAVILY_API_KEY = _clean_env(os.environ.get("TAVILY_API_KEY"))
HF_TOKEN = _clean_env(os.environ.get("HF_TOKEN", ""))

# Load configured Supadata Keys dynamically
SUPADATA_KEYS = [
    cleaned for i in range(1, 5)
    if (cleaned := _clean_env(os.environ.get(f"SUPADATA_KEY_{i}") or os.environ.get(f"SUPADATA_KEY_{['ONE','TWO','THREE','FOUR'][i-1]}")))
]

# --- Ollama Configuration (For Video Summaries & Chat with Fallback Keys) ---
OLLAMA_API_KEYS = [
    cleaned for key in [
        os.environ.get("OLLAMA_API_KEY_ONE") or os.environ.get("OLLAMA_API_KEY_1"),
        os.environ.get("OLLAMA_API_KEY_SECOND") or os.environ.get("OLLAMA_API_KEY_TWO") or os.environ.get("OLLAMA_API_KEY_2"),
        os.environ.get("OLLAMA_API_KEY_THIRD") or os.environ.get("OLLAMA_API_KEY_THREE") or os.environ.get("OLLAMA_API_KEY_3"),
        os.environ.get("OLLAMA_API_KEY"),
        os.environ.get("OLLAMA"),
    ]
    if (cleaned := _clean_env(key))
]
# Deduplicate while preserving order
OLLAMA_API_KEYS = list(dict.fromkeys(OLLAMA_API_KEYS))
OLLAMA_API_KEY = OLLAMA_API_KEYS[0] if OLLAMA_API_KEYS else ""
OLLAMA_HOST = _clean_env(os.environ.get("OLLAMA_HOST", "https://ollama.com"))
OLLAMA_SUMMARY_MODEL = _clean_env(os.environ.get("OLLAMA_SUMMARY_MODEL", "gpt-oss:20b"))
OLLAMA_MODEL = _clean_env(os.environ.get("OLLAMA_MODEL")) or OLLAMA_SUMMARY_MODEL

# --- Ephemeral Vector Store Cache Configuration ---
MAX_ACTIVE_VIDEOS = int(_clean_env(os.environ.get("MAX_ACTIVE_VIDEOS", "10")) or "10")
VIDEO_INACTIVITY_TTL_MINUTES = int(_clean_env(os.environ.get("VIDEO_INACTIVITY_TTL_MINUTES", "45")) or "45")

