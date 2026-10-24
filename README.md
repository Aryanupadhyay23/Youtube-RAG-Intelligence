# YouTube Intelligence Assistant

An AI-powered assistant that lets you chat with any YouTube video. Simply paste a YouTube link to ask questions, jump to exact video timestamps, generate structured summaries, and search full transcripts.

---

## Key Features

- **💬 Interactive Video Chat:** Ask any question about a video and get direct answers backed by the video's content.
- **⏱️ Clickable Timestamps:** Jump straight to the exact moment in the video where a topic is discussed.
- **📝 Instant Summaries:** Generate clear overviews and key takeaways from long videos in seconds.
- **🔍 Transcript Explorer:** Browse, search, and review the full video transcript with ease.
- **💾 Saved Conversations:** Keep track of previous chats and review them anytime.
- **🌐 Smart Search:** Finds answers directly from the video or searches the web if additional context is needed.

---

## How It Works

1. **Paste a Link:** Provide any public YouTube video URL.
2. **Process Video:** The app fetches the video details and transcript.
3. **Chat & Explore:** Ask questions, read summaries, and jump to specific timestamps through an easy-to-use web interface.

---

## Getting Started

### Prerequisites

- **Python 3.12+** installed on your system, or **Docker**.
- API keys for AI services (see [Configuration](#configuration)).

---

### Local Setup

#### 1. Clone the repository
```bash
git clone https://github.com/Aryanupadhyay23/Youtube-RAG-Intelligence.git
cd Youtube-RAG-Intelligence
```

#### 2. Create a virtual environment
```bash
python -m venv .venv

# On Windows (PowerShell)
.venv\Scripts\Activate.ps1

# On macOS / Linux
source .venv/bin/activate
```

#### 3. Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Configure environment variables
Create a `.env` file by copying the example template:
```bash
cp .env.example .env
```
Fill in your API keys in the `.env` file (see the [Configuration](#configuration) section below).

#### 5. Run the application
Run the backend and frontend in two separate terminals:

```bash
# Terminal 1: Backend API
uvicorn backend.main:app --reload --port 8000
```

```bash
# Terminal 2: Web Interface
streamlit run frontend/app.py --server.port 8501
```

Once running, open your browser and navigate to:
- **Web App:** [http://localhost:8501](http://localhost:8501)
- **API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Running with Docker

You can run the entire application using Docker with a single command:

```bash
# Build the Docker image
docker build -t youtube-assistant .

# Run the container
docker run -p 7860:7860 -p 8000:8000 --env-file .env youtube-assistant
```

Access the web interface at **http://localhost:7860**.

---

## Configuration

Set up the following variables in your `.env` file:

| Variable | Description | Required |
|---|---|:---:|
| `OLLAMA_API_KEY_ONE` | API key for Ollama AI model | Yes |
| `OLLAMA_HOST` | Ollama service endpoint (e.g., `https://ollama.com`) | Yes |
| `OLLAMA_MODEL` | Name of the AI chat model | Yes |
| `OLLAMA_SUMMARY_MODEL` | Name of the summary model | Yes |
| `GOOGLE_API_KEY` | Google Gemini API key | Yes |
| `SUPADATA_KEY_ONE` | Supadata API key for fetching video transcripts | Yes |
| `QDRANT_CLUSTER_ENDPOINT`| Qdrant Cloud cluster endpoint | Yes |
| `QDRANT_API_KEY` | Qdrant Cloud API key | Yes |
| `QDRANT_COLLECTION` | Name of the vector collection | Yes |
| `UPSTASH_REDIS_REST_URL` | Upstash Redis URL for saving chat history | Optional |
| `UPSTASH_REDIS_REST_TOKEN` | Upstash Redis token | Optional |
| `TAVILY_API_KEY` | Tavily API key for web search fallback | Optional |
| `BACKEND_API_URL` | URL connecting frontend to backend (default: `http://127.0.0.1:8000`) | Yes |

---

## Project Structure

```text
Youtube-RAG-Intelligence/
├── backend/          # API services, search logic, and routes
├── frontend/         # Streamlit web interface and UI components
├── tests/            # Test suite
├── Dockerfile        # Container setup for production and local use
├── requirements.txt  # Python package dependencies
├── .env.example      # Example environment variables template
└── README.md         # Project documentation
```

---

## Testing

To run tests:

```bash
pytest
```
