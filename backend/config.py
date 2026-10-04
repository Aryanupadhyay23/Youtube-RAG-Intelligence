import os
from dotenv import load_dotenv

from backend.utils.constants import *

# Load .env file
load_dotenv(override=False)

# API Keys
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
HF_TOKEN = os.environ.get("HF_TOKEN", "")

# Load configured Supadata Keys dynamically
SUPADATA_KEYS = [
    key for i in range(1, 5)
    if (key := os.environ.get(f"SUPADATA_KEY_{i}") or os.environ.get(f"SUPADATA_KEY_{['ONE','TWO','THREE','FOUR'][i-1]}"))
]

# Ollama Host & Key Configuration
OLLAMA_API_KEY = os.environ.get("OLLAMA") or os.environ.get("OLLAMA_API_KEY", "")
OLLAMA_HOST = os.environ.get("OLLAMA_HOST") or os.environ.get("OLLAMA_BASE_URL", "https://ollama.com")
