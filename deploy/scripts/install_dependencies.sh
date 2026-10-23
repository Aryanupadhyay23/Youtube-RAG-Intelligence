#!/bin/bash
set -e

# Prerequisites for AWS CLI v2 extraction & download (needed regardless of Docker state)
if ! command -v unzip &> /dev/null || ! command -v curl &> /dev/null; then
    apt-get update -y
    apt-get install -y unzip curl
fi

# Update and install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    apt-get update -y
    apt-get install -y docker.io
    systemctl enable docker
    systemctl start docker
    usermod -aG docker ubuntu
fi

# Ensure docker daemon always starts on system boot
systemctl enable docker
systemctl start docker

# Install AWS CLI v2 if not present
if ! command -v aws &> /dev/null; then
    echo "Installing AWS CLI..."
    curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
    unzip -q awscliv2.zip
    ./aws/install
    rm -rf aws awscliv2.zip
fi

echo "Dependencies ready."
