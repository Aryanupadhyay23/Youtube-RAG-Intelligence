FROM python:3.11-slim

# HuggingFace Spaces requires a non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# HuggingFace Spaces expects port 7860
EXPOSE 7860

ENV PYTHONUNBUFFERED=1

# Disable Streamlit's dev warnings + bind to all interfaces
CMD ["streamlit", "run", "app.py", \
     "--server.port=7860", \
     "--server.address=0.0.0.0", \
     "--server.fileWatcherType=none", \
     "--browser.gatherUsageStats=false"]