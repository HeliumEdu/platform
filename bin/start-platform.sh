#!/usr/bin/env bash
#
# Start the Helium platform Docker containers for local integration testing.
#
# This script is self-contained and fetches all necessary files from GitHub.
# It does not require a local clone of the platform repository.
#
# Environment variables:
#   PLATFORM_RESOURCE_IMAGE    - ECR image for resource container (optional)
#   PLATFORM_API_IMAGE         - ECR image for API container (optional)
#   PLATFORM_WORKER_IMAGE      - ECR image for worker container (optional)
#   PLATFORM                   - Architecture: arm64 or amd64 (default: arm64)
#   PLATFORM_BRANCH            - GitHub branch to fetch configs from (default: main)
#
# If PLATFORM_*_IMAGE vars are set, those specific images are used.
# Otherwise, images are pulled from ECR Public.
#

set -e

PLATFORM="${PLATFORM:-arm64}"
PLATFORM_BRANCH="${PLATFORM_BRANCH:-main}"
GITHUB_RAW_URL="https://raw.githubusercontent.com/HeliumEdu/platform/${PLATFORM_BRANCH}"
WORK_DIR="${TMPDIR:-/tmp}/helium-platform"

echo "Starting platform containers..."

# Create working directory
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Fetch docker-compose.yml and .env from GitHub
echo "Fetching configuration from GitHub (branch: $PLATFORM_BRANCH)..."
curl -fsSL "$GITHUB_RAW_URL/docker-compose.yml" -o docker-compose.yml
curl -fsSL "$GITHUB_RAW_URL/.env.docker.example" -o .env

# Fetch localstack init script
mkdir -p container
curl -fsSL "$GITHUB_RAW_URL/container/init-localstack.py" -o container/init-localstack.py

# Export image variables for docker-compose (default to ECR Public)
export PLATFORM
export PLATFORM_RESOURCE_IMAGE="${PLATFORM_RESOURCE_IMAGE:-public.ecr.aws/heliumedu/helium/platform-resource:${PLATFORM}-latest}"
export PLATFORM_API_IMAGE="${PLATFORM_API_IMAGE:-public.ecr.aws/heliumedu/helium/platform-api:${PLATFORM}-latest}"
export PLATFORM_WORKER_IMAGE="${PLATFORM_WORKER_IMAGE:-public.ecr.aws/heliumedu/helium/platform-worker:${PLATFORM}-latest}"

echo "Using images:"
echo "  Resource: $PLATFORM_RESOURCE_IMAGE"
echo "  API:      $PLATFORM_API_IMAGE"
echo "  Worker:   $PLATFORM_WORKER_IMAGE"

# Check if we can authenticate with AWS (for CI environments)
USE_ECR_AUTH=false
if [[ "$PLATFORM_API_IMAGE" == *"public.ecr.aws"* ]]; then
    if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null 2>&1; then
        echo "Logging in to ECR Public to avoid rate limits..."
        if aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/heliumedu 2>/dev/null; then
            USE_ECR_AUTH=true
            echo "Pulling images from ECR..."
            docker pull "$PLATFORM_RESOURCE_IMAGE"
            docker pull "$PLATFORM_API_IMAGE"
            docker pull "$PLATFORM_WORKER_IMAGE"
        fi
    fi
fi

# Start containers
echo "Starting Docker containers..."
if [[ "$USE_ECR_AUTH" == "true" ]]; then
    # Use normal docker-compose (already authenticated)
    docker compose up -d
else
    # Logout from ECR to prevent credential helper from being invoked
    docker logout public.ecr.aws 2>/dev/null || true
    docker compose up -d --pull missing
fi

# Wait for API to be ready
echo "Waiting for platform API to be ready..."
for i in $(seq 1 60); do
    if curl -s http://localhost:8000/health/ > /dev/null 2>&1; then
        echo "Platform API is ready!"
        exit 0
    fi
    echo "Waiting for API... ($i/60)"
    sleep 2
done

echo "Error: Platform API did not become ready within 120 seconds"
exit 1
