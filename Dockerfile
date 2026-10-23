# ==========================================
# Stage 1: Builder (Compiles C/C++ extensions)
# ==========================================
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install compiler tools required for building native wheels (e.g. chroma-hnswlib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create isolated virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    # Strip unnecessary files and test directories from virtual environment to minimize size
    find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyc" -delete && \
    find /opt/venv -type f -name "*.pyo" -delete && \
    find /opt/venv -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type d -name "test" -exec rm -rf {} + 2>/dev/null || true

# ==========================================
# Stage 2: Final Minimal Runtime Stage
# ==========================================
FROM python:3.12-slim AS runner

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy only the compiled virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy only the necessary runtime code
COPY --chown=appuser:appuser backend /app/backend
COPY --chown=appuser:appuser frontend /app/frontend

# Streamlit loads its config from the working directory (/app)
COPY --chown=appuser:appuser frontend/.streamlit /app/.streamlit

# Create and grant permissions for logs directory
RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs && chmod 775 /app/logs

# Run as non-root user
USER appuser

# Streamlit UI container port
EXPOSE 7860

# Container health: backend /health endpoint is env-independent
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)" || exit 1

# Run both servers under a single supervisor shell: if either process dies the
# container exits (and --restart unless-stopped brings it back) instead of
# silently serving only one side.
CMD ["bash", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port 8000 & UVICORN_PID=$!; streamlit run frontend/app.py --server.port=7860 --server.address=0.0.0.0 --server.fileWatcherType=none --browser.gatherUsageStats=false & STREAMLIT_PID=$!; wait -n; EXIT_CODE=$?; echo 'A server process exited; stopping container.'; kill $UVICORN_PID $STREAMLIT_PID 2>/dev/null || true; exit $EXIT_CODE"]