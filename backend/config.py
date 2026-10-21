import os
import socket
from dotenv import load_dotenv

# Prioritize IPv4 addresses during DNS resolution to avoid 20-45s IPv6 SYN timeouts on Windows/cloud
def _enable_ipv4_preference():
    orig_getaddrinfo = socket.getaddrinfo
    def ipv4_preferred_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
        try:
            res = orig_getaddrinfo(host, port, family, type, proto, flags)
            return sorted(res, key=lambda x: 0 if x[0] == socket.AF_INET else 1)
        except Exception:
            return orig_getaddrinfo(host, port, family, type, proto, flags)
    socket.getaddrinfo = ipv4_preferred_getaddrinfo

_enable_ipv4_preference()

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


GOOGLE_API_KEY = _clean_env(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
TAVILY_API_KEY = _clean_env(os.environ.get("TAVILY_API_KEY"))

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
OLLAMA_HOST = _clean_env(os.environ.get("OLLAMA_HOST", "https://ollama.com"))
OLLAMA_SUMMARY_MODEL = _clean_env(os.environ.get("OLLAMA_SUMMARY_MODEL", "gemma4:31b-cloud"))
OLLAMA_MODEL = _clean_env(os.environ.get("OLLAMA_MODEL")) or OLLAMA_SUMMARY_MODEL
OLLAMA_NUM_CTX = int(_clean_env(os.environ.get("OLLAMA_NUM_CTX", "131072")) or "131072")


# --- Ephemeral Vector Store Cache Configuration ---
MAX_ACTIVE_VIDEOS = int(_clean_env(os.environ.get("MAX_ACTIVE_VIDEOS", "10")) or "10")
VIDEO_INACTIVITY_TTL_MINUTES = int(_clean_env(os.environ.get("VIDEO_INACTIVITY_TTL_MINUTES", "45")) or "45")

# --- Upstash Redis Conversation Memory Configuration ---
UPSTASH_REDIS_REST_URL = _clean_env(os.environ.get("UPSTASH_REDIS_REST_URL"))
UPSTASH_REDIS_REST_TOKEN = _clean_env(os.environ.get("UPSTASH_REDIS_REST_TOKEN"))
REDIS_URL = _clean_env(os.environ.get("REDIS_URL"))
if not REDIS_URL and UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN:
    host = UPSTASH_REDIS_REST_URL.replace("https://", "").replace("http://", "").rstrip("/")
    REDIS_URL = f"rediss://default:{UPSTASH_REDIS_REST_TOKEN}@{host}:6379"


