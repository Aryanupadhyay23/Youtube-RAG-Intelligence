import os
from dotenv import load_dotenv

from backend.utils.constants import *

# Load .env file
load_dotenv(override=True)

# --- Groq Configuration (Qwen 3.8 27B with 3 Fallback Keys) ---
GROQ_API_KEYS = [
    key for key in [
        os.environ.get("GROQ_API_KEY_1"),
        os.environ.get("GROQ_API_KEY_2"),
        os.environ.get("GROQ_API_KEY_3"),
        os.environ.get("GROQ_API_KEY"),
    ]
    if key and key.strip()
]
GROQ_MODEL = os.environ.get("GROQ_MODEL") or LLM_MODEL

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Load configured Supadata Keys dynamically
SUPADATA_KEYS = [
    key for i in range(1, 5)
    if (key := os.environ.get(f"SUPADATA_KEY_{i}") or os.environ.get(f"SUPADATA_KEY_{['ONE','TWO','THREE','FOUR'][i-1]}"))
]

# --- Ollama Configuration (For Video Summaries & Chat with Fallback Keys) ---
OLLAMA_API_KEYS = [
    key for key in [
        os.environ.get("OLLAMA_API_KEY_ONE") or os.environ.get("OLLAMA_API_KEY_1"),
        os.environ.get("OLLAMA_API_KEY_SECOND") or os.environ.get("OLLAMA_API_KEY_TWO") or os.environ.get("OLLAMA_API_KEY_2"),
        os.environ.get("OLLAMA_API_KEY_THIRD") or os.environ.get("OLLAMA_API_KEY_THREE") or os.environ.get("OLLAMA_API_KEY_3"),
        os.environ.get("OLLAMA_API_KEY"),
        os.environ.get("OLLAMA"),
    ]
    if key and key.strip()
]
# Deduplicate while preserving order
OLLAMA_API_KEYS = list(dict.fromkeys(OLLAMA_API_KEYS))
OLLAMA_API_KEY = OLLAMA_API_KEYS[0] if OLLAMA_API_KEYS else ""
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "https://ollama.com")
OLLAMA_SUMMARY_MODEL = os.environ.get("OLLAMA_SUMMARY_MODEL", "gpt-oss:20b")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL") or OLLAMA_SUMMARY_MODEL

