APP_TITLE = "YouTube RAG Intelligence"

APP_CAPTION = (
    "Supadata • Groq LLaMA 3.3 • "
    "HuggingFace • FAISS"
)

MEMORY_WINDOW = 10

CHUNK_SIZE = 1000

CHUNK_OVERLAP = 200

SUMMARY_CHUNK_SIZE = 8000

SUMMARY_CHUNK_OVERLAP = 400

RETRIEVER_K = 4

LLM_MODEL = "llama-3.3-70b-versatile"

LLM_TEMPERATURE = 0.3

LLM_MAX_TOKENS = 2048

EMBEDDING_MODEL = (
    "sentence-transformers/"
    "all-MiniLM-L6-v2"
)

QUICK_QUESTIONS = [
    "What is the main topic?",
    "What are the key takeaways?",
    "Who is speaking?",
    "What conclusions are drawn?",
    "Are there any statistics mentioned?",
    "What problems are discussed?",
]