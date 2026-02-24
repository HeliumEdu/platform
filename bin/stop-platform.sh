#!/usr/bin/env bash
#
# Stop the Helium platform Docker containers.
#
# This script stops containers started by start-platform.sh.
# It uses the same working directory where docker-compose.yml was fetched.
#
# Environment variables:
#   PLATFORM_CLEANUP - Set to "true" to also remove volumes (default: false)
#

set -e

WORK_DIR="${TMPDIR:-/tmp}/helium-platform"

echo "Stopping platform containers..."

if [ ! -d "$WORK_DIR" ]; then
    echo "Warning: Platform working directory not found at $WORK_DIR"
    echo "Containers may not have been started or were already cleaned up."
    exit 0
fi

cd "$WORK_DIR"

if [ "$PLATFORM_CLEANUP" = "true" ]; then
    echo "Stopping and removing containers, networks, and volumes..."
    docker compose down -v
    rm -rf "$WORK_DIR"
else
    docker compose stop
fi

echo "Platform containers stopped."
