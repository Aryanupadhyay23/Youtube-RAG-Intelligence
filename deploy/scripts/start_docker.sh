#!/bin/bash
set -e

AWS_REGION="ap-southeast-2"
ECR_REPOSITORY="youtube-rag-intelligence"

# Fetch Account ID dynamically via AWS STS or instance metadata
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --region ${AWS_REGION} --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
IMAGE_URI="${ECR_REGISTRY}/${ECR_REPOSITORY}:latest"

echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}

echo "Pulling latest image: ${IMAGE_URI}..."
docker pull ${IMAGE_URI}

echo "Starting container..."
# Run container mapping port 80 (standard HTTP) to Streamlit (7860) and port 8000 for FastAPI
# If an .env exists in /home/ubuntu or /home/ubuntu/app, sanitize and inject it
ENV_FLAG=""
ENV_FILE=""
if [ -f "/home/ubuntu/.env" ]; then
    ENV_FILE="/home/ubuntu/.env"
elif [ -f "/home/ubuntu/app/.env" ]; then
    ENV_FILE="/home/ubuntu/app/.env"
fi

if [ -n "$ENV_FILE" ]; then
    # Strip carriage returns and remove any spaces around '=' to satisfy Docker's strict env parser
    sed -i 's/\r$//' "$ENV_FILE"
    sed -i 's/[[:space:]]*=[[:space:]]*/=/' "$ENV_FILE"
    # Strip enclosing quotes around values because Docker preserves literal quotes
    sed -i -E 's/="?([^"]*)"?$/=\1/' "$ENV_FILE"
    ENV_FLAG="--env-file $ENV_FILE"
fi

docker run -d \
    --name youtube-rag-container \
    --restart unless-stopped \
    -p 80:7860 \
    -p 8000:8000 \
    $ENV_FLAG \
    ${IMAGE_URI}

# Ensure restart policy is explicitly set so container starts automatically on EC2 reboot
docker update --restart unless-stopped youtube-rag-container

echo "YouTube RAG Intelligence started successfully with automatic restart policy."
