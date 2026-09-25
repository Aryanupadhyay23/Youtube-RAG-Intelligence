APP_TITLE = "YouTube RAG Intelligence"

APP_CAPTION = (
    "AI-Powered Chat, Summaries, and Transcript Explorer"
)

MEMORY_WINDOW = 10

CHUNK_SIZE = 1000

CHUNK_OVERLAP = 200

SUMMARY_CHUNK_SIZE = 8000

SUMMARY_CHUNK_OVERLAP = 400

RETRIEVER_K = 4

SEMANTIC_TOP_K = 20
BM25_TOP_K = 20
FINAL_TOP_K = 5
RRF_K = 60
MAX_RETRIEVAL_ATTEMPTS = 2
RECENT_MESSAGE_COUNT = 6

LLM_MODEL = "openai/gpt-oss-120b"

LLM_TEMPERATURE = 0.3



EMBEDDING_MODEL = "models/gemini-embedding-2"

QUICK_QUESTIONS = [
    "What is the main topic?",
    "What are the key takeaways?",
    "Who is speaking?",
    "What conclusions are drawn?",
    "Are there any statistics mentioned?",
    "What problems are discussed?",
]