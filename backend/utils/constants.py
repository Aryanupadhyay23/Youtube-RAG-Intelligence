APP_TITLE = "YouTube RAG Intelligence"
APP_CAPTION = "AI-Powered Chat, Summaries, and Transcript Explorer"

# Conversation Memory
MEMORY_WINDOW = 5

# Chunking Parameters
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Summarization Parameters
SUMMARY_CHUNK_SIZE = 8000
SUMMARY_CHUNK_OVERLAP = 400

# Retrieval & Fusion Parameters
SEMANTIC_TOP_K = 20
BM25_TOP_K = 20
FINAL_TOP_K = 5
RRF_K = 60
MAX_RETRIEVAL_ATTEMPTS = 2

# Model Names
LLM_MODEL = "openai/gpt-oss-120b"
SUMMARY_MODEL = "gpt-oss:120b-cloud"
EMBEDDING_MODEL = "models/gemini-embedding-2"
LLM_TEMPERATURE = 0.3

# Suggested Questions
QUICK_QUESTIONS = [
    "What is the main topic?",
    "What are the key takeaways?",
    "Who is speaking?",
    "What conclusions are drawn?",
    "Are there any statistics mentioned?",
    "What problems are discussed?",
]
