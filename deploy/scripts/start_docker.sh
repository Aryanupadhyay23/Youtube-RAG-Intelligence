#!/bin/bash
set -e

AWS_REGION="ap-southeast-2"
ECR_REPOSITORY="youtube-rag-intelligence"
CONTAINER_NAME="youtube-rag-container"

# Fetch AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity \
    --region "${AWS_REGION}" \
    --query Account \
    --output text)

ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:latest"

echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region "${AWS_REGION}" |
    docker login --username AWS --password-stdin "${ECR_REGISTRY}"

echo "Pulling latest image: ${IMAGE_URI}..."
docker pull "${IMAGE_URI}"

# Locate environment file
ENV_FILE=""
if [ -f "/home/ubuntu/.env" ]; then
    ENV_FILE="/home/ubuntu/.env"
elif [ -f "/home/ubuntu/app/.env" ]; then
    ENV_FILE="/home/ubuntu/app/.env"
fi

ENV_ARGS=()
if [ -n "${ENV_FILE}" ]; then
    echo "Using environment file: ${ENV_FILE}"
    # Strip CR characters without mutating the operator's file
    SANITIZED_ENV="/tmp/youtube-rag.env"
    sed 's/\r$//' "${ENV_FILE}" > "${SANITIZED_ENV}"
    ENV_ARGS=(--env-file "${SANITIZED_ENV}")
fi

echo "Stopping existing container if present..."
if docker container inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
    docker rm -f "${CONTAINER_NAME}"
fi

echo "Starting YouTube RAG container..."

docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    -p 7860:7860 \
    -p 8000:8000 \
    "${ENV_ARGS[@]}" \
    "${IMAGE_URI}" \
    bash -c '
        uvicorn backend.main:app \
            --host 0.0.0.0 \
            --port 8000 \
            --root-path /youtube-rag-backend &

        UVICORN_PID=$!
        streamlit run frontend/app.py \
            --server.port=7860 \
            --server.address=0.0.0.0 \
            --server.baseUrlPath=youtube-rag \
            --server.fileWatcherType=none \
            --browser.gatherUsageStats=false &

        STREAMLIT_PID=$!
        trap "kill $UVICORN_PID $STREAMLIT_PID 2>/dev/null" EXIT
        wait -n
        exit $?
    '

echo "YouTube RAG container started."
echo "Frontend: http://aryan-projects.duckdns.org/youtube-rag/"
echo "Backend docs: http://aryan-projects.duckdns.org/youtube-rag-backend/docs"
