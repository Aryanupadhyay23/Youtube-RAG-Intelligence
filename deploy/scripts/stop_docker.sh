#!/bin/bash
echo "Stopping existing YouTube RAG container if running..."
if command -v docker &> /dev/null; then
    docker stop youtube-rag-container 2>/dev/null || true
    docker rm youtube-rag-container 2>/dev/null || true
fi
