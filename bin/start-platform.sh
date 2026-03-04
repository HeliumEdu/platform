#!/usr/bin/env bash
#
# Start the Helium platform Docker containers for local integration testing.
#
# This script is self-contained and fetches all necessary files from GitHub.
# It does not require a local clone of the platform repository.
#
# Environment variables:
#   REGISTRY_PREFIX            - Registry prefix (e.g., "public.ecr.aws/heliumedu/") - auto-detected if not set
#   PLATFORM_RESOURCE_IMAGE    - Full image for resource container (optional, overrides REGISTRY_PREFIX)
#   PLATFORM_API_IMAGE         - Full image for API container (optional, overrides REGISTRY_PREFIX)
#   PLATFORM_WORKER_IMAGE      - Full image for worker container (optional, overrides REGISTRY_PREFIX)
#   PLATFORM                   - Architecture: arm64 or amd64 (default: arm64)
#   PLATFORM_BRANCH            - GitHub branch to fetch configs from (default: main)
#
# If local images exist, they are used. Otherwise, images are pulled from ECR Public.
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

# Determine registry prefix - prefer local images if available
export PLATFORM
if [[ -z "${REGISTRY_PREFIX:-}" ]]; then
    LOCAL_API_IMAGE="helium/platform-api:${PLATFORM}-latest"
    if docker image inspect "$LOCAL_API_IMAGE" &>/dev/null; then
        echo "Using local images..."
        export REGISTRY_PREFIX=""
    else
        echo "Local images not found, will pull from ECR Public..."
        export REGISTRY_PREFIX="public.ecr.aws/heliumedu/"
    fi
else
    echo "Using provided REGISTRY_PREFIX: $REGISTRY_PREFIX"
fi

echo "Registry prefix: ${REGISTRY_PREFIX:-<local>}"

# Check if we can authenticate with AWS (for CI environments)
USE_ECR_AUTH=false
if [[ "$REGISTRY_PREFIX" == *"public.ecr.aws"* ]]; then
    if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null 2>&1; then
        echo "Logging in to ECR Public to avoid rate limits..."
        if aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/heliumedu 2>/dev/null; then
            USE_ECR_AUTH=true
            echo "Pulling images from ECR..."
            docker pull "${REGISTRY_PREFIX}helium/platform-resource:${PLATFORM}-latest"
            docker pull "${REGISTRY_PREFIX}helium/platform-api:${PLATFORM}-latest"
            docker pull "${REGISTRY_PREFIX}helium/platform-worker:${PLATFORM}-latest"
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
    if curl -s http://localhost:8000/status/ > /dev/null 2>&1; then
        echo "Platform API is ready!"
        exit 0
    fi
    echo "Waiting for API... ($i/60)"
    sleep 2
done

echo "Error: Platform API did not become ready within 120 seconds"
exit 1
