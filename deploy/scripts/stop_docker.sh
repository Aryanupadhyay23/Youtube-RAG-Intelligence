#!/bin/bash
echo "Stopping existing YouTube RAG container if running..."
docker stop youtube-rag-container || true
docker rm youtube-rag-container || true
