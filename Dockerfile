FROM python:3.12-slim

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install build tools (needed for chroma-hnswlib) and dependencies
COPY requirements.txt .

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy application files
COPY --chown=appuser:appuser . .

# Run as non-root user
USER appuser

# Hugging Face Spaces public port
EXPOSE 7860

ENV PYTHONUNBUFFERED=1

# Start FastAPI internally and Streamlit publicly
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port 8000 & exec streamlit run app.py --server.port=7860 --server.address=0.0.0.0 --server.fileWatcherType=none --browser.gatherUsageStats=false"]