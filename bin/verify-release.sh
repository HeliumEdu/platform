#!/usr/bin/env bash
# Verifies a platform release's containers exist in ECR before deploying it.
#
# Usage: bin/verify-release.sh <version>

set -euo pipefail

VERSION="${1:?Usage: bin/verify-release.sh <version>}"

echo "Verifying containers exist for version $VERSION ..."
for container in platform-resource platform-api platform-worker; do
  echo "  Checking $container:amd64-$VERSION ..."
  if ! error="$(aws ecr-public describe-images --repository-name "helium/$container" \
    --image-ids "imageTag=amd64-$VERSION" --region us-east-1 2>&1 >/dev/null)"; then
    echo "✗ Container public.ecr.aws/heliumedu/helium/$container:amd64-$VERSION not found: $error" >&2
    exit 1
  fi
  echo "  ✓ $container:amd64-$VERSION found"
done
echo "✓ All containers found"
