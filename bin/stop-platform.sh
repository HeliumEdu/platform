#!/usr/bin/env bash
#
# Stop the Helium platform Docker containers.
#
# This script stops containers started by start-platform.sh.
# It uses the same working directory where docker-compose.yml was fetched.
#

set -euo pipefail

WORK_DIR="${TMPDIR:-/tmp}/helium-platform"

echo "Stopping platform containers ..."

if [ ! -d "$WORK_DIR" ]; then
    echo "Warning: Platform working directory not found at $WORK_DIR"
    echo "Containers may not have been started or were already cleaned up."
    exit 0
fi

cd "$WORK_DIR"

docker compose stop

echo "Platform containers stopped."
