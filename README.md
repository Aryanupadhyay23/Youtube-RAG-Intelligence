# YouTube RAG Intelligence

An AI-powered YouTube video assistant built with LangChain, Groq LLaMA 3.3, HuggingFace embeddings, and FAISS. Chat with any video, generate summaries, and explore transcripts.

> Transcripts in any language are automatically answered in English.

## Live Demo

[YouTube RAG Intelligence on HuggingFace](https://huggingface.co/spaces/Aryan2301/YouTube_RAG_Intelligence)

---

## Features

- **RAG Chat** - Ask questions grounded strictly in transcript context with token-by-token streaming
- **Smart Summary** - Map-reduce summarisation for any video length
- **Transcript Explorer** - Search keywords and jump to YouTube timestamps
- **Multi-language** - Transcripts in any language; responses always in English
- **Multi-chat** - Create, switch, and delete multiple chat sessions
- **Export** - Download chat history and summaries as `.txt` or `.md`

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Groq LLaMA 3.3 70B |
| Orchestration | LangChain |
| Embeddings | HuggingFace all-MiniLM-L6-v2 |
| Vector Store | FAISS (CPU) |
| Transcripts | Supadata API |
| UI | Streamlit |
| Runtime | Python 3.11 |

---

## Project Structure

```
app.py                        <- Streamlit entry point
config.py                     <- API keys + environment detection
requirements.txt
Dockerfile
assets/
    styles.css
core/
    __init__.py
    embeddings.py
    llm.py
    prompts.py
    rag.py
    summary.py
    vectorstore.py
exports/
    __init__.py
    export_chat.py
    export_summary.py
services/
    __init__.py
    chat_service.py
    transcript_service.py
    youtube_service.py
ui/
    __init__.py
    chat_ui.py
    landing.py
    sidebar.py
    summary_ui.py
    transcript_ui.py
utils/
    __init__.py
    constants.py
    formatting.py
    helpers.py
    session.py
```

---

## Local Setup

### 1. Clone

```bash
git clone https://github.com/your-username/youtube-rag-intelligence.git
cd youtube-rag-intelligence
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Linux / Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Create .env

Create a `.env` file in the root of the project:

```env
GROQ_API_KEY=your_groq_api_key_here
SUPADATA_KEY_1=your_supadata_key_here
SUPADATA_KEY_2=your_second_supadata_key_here
SUPADATA_KEY_3=your_third_supadata_key_here
HF_TOKEN=your_huggingface_token_here
```

> Never commit `.env` to git. It is already listed in `.gitignore`.

### 5. Run

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## HuggingFace Spaces Deployment

### Step 1 - Create a New Space

1. Go to https://huggingface.co/new-space
2. Fill in:
   - Space name: `youtube-rag-intelligence` (or your choice)
   - License: `MIT`
   - SDK: `Docker`  <-- important, NOT Streamlit SDK
   - Visibility: Public or Private

### Step 2 - Add Secrets

Do NOT put API keys in code or README. Use HuggingFace Secrets only.

Go to your Space -> Settings -> Variables and Secrets -> New Secret

Add each of the following:

| Secret Name | Required | Where to Get It |
|---|---|---|
| `GROQ_API_KEY` | Required | https://console.groq.com |
| `SUPADATA_KEY_1` | Required | https://supadata.ai |
| `SUPADATA_KEY_2` | Optional | Fallback if key 1 hits rate limit |
| `SUPADATA_KEY_3` | Optional | Fallback if key 2 hits rate limit |
| `HF_TOKEN` | Optional | https://huggingface.co/settings/tokens |

Secrets are injected into `os.environ` automatically before the app starts.
The app detects HuggingFace via the `SPACE_ID` env variable and skips `.env` loading entirely.

### Step 3 - Upload Project Files

Upload all files and folders EXCEPT:

```
.env
venv/
__pycache__/
*.pyc
*.pyo
.DS_Store
```

Required files to upload:

```
app.py
config.py
requirements.txt
Dockerfile
README.md
assets/
core/
exports/
services/
ui/
utils/
```

### Step 4 - Verify Deployment

Once the Space builds and starts:

1. Open the Space URL
2. Check the sidebar - it shows:
   - "Running on HuggingFace Spaces"
   - "GROQ_API_KEY loaded"
   - "SUPADATA_KEY (N keys loaded)"
3. If any key shows missing, go back to Settings -> Secrets and verify the name matches exactly

---

## Environment Variables Reference

| Variable | Local (.env) | HuggingFace (Secrets) | Required |
|---|---|---|---|
| `GROQ_API_KEY` | Yes | Yes | Required |
| `SUPADATA_KEY_1` | Yes | Yes | Required |
| `SUPADATA_KEY_2` | Yes | Yes | Optional |
| `SUPADATA_KEY_3` | Yes | Yes | Optional |
| `HF_TOKEN` | Yes | Yes | Optional |

---

## How Environment Detection Works

```
App starts
    |
    |-- SPACE_ID in os.environ?
    |       |
    |       |-- YES -> HuggingFace Spaces
    |       |         Secrets already in os.environ
    |       |         load_dotenv() is skipped
    |       |
    |       |-- NO  -> Local machine
    |                 load_dotenv() reads .env file
    |                 Keys loaded into os.environ
    |
    |-- os.environ.get("GROQ_API_KEY") works the same in both cases
```

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `GROQ_API_KEY is not set` | Secret not added or wrong name | Settings -> Secrets, check key is named exactly `GROQ_API_KEY` |
| `No Supadata API keys configured` | `SUPADATA_KEY_1` missing | Add it in Settings -> Secrets |
| `Space failed to build` | Dependency version conflict | Check `requirements.txt` versions are pinned exactly |
| `Empty transcript returned` | Video has no captions | Try a video with auto-generated or manual captions enabled |
| `Invalid YouTube URL` | Wrong URL format | Use `https://youtube.com/watch?v=VIDEO_ID` format |

---

## License

MIT License