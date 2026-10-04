#!/bin/bash
set -e

AWS_REGION="us-east-1"
ECR_REPOSITORY="youtube-rag-intelligence"

# Fetch Account ID dynamically via AWS STS or instance metadata
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:latest"

echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

echo "Pulling latest image: ${IMAGE_URI}..."
docker pull ${IMAGE_URI}

echo "Starting container..."
# Run container mapping port 80 (standard HTTP) to Streamlit (7860) and port 8000 for FastAPI
# If an /home/ubuntu/.env exists, mount or inject it
ENV_FLAG=""
if [ -f "/home/ubuntu/.env" ]; then
    ENV_FLAG="--env-file /home/ubuntu/.env"
fi

docker run -d \
    --name youtube-rag-container \
    --restart unless-stopped \
    -p 80:7860 \
    -p 8000:8000 \
    $ENV_FLAG \
    ${IMAGE_URI}

echo "YouTube RAG Intelligence started successfully."
