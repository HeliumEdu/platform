#!/usr/bin/env python3

"""
Verify a platform release's containers exist in ECR before deploying it.
"""

import argparse
import subprocess
import sys


def verify_containers_exist(version, aws_region="us-east-1"):
    """Verify that all platform containers exist in ECR for the given version."""
    print(f"Verifying containers exist for version {version} ...")

    containers = ["platform-resource", "platform-api", "platform-worker"]

    for container in containers:
        print(f"  Checking {container}:amd64-{version} ...")

        result = subprocess.run(
            [
                "aws", "ecr-public", "describe-images",
                "--repository-name", f"helium/{container}",
                "--image-ids", f"imageTag=amd64-{version}",
                "--region", aws_region
            ],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print(f"✗ Container public.ecr.aws/heliumedu/helium/{container}:amd64-{version} not found")
            return False

        print(f"  ✓ {container}:amd64-{version} found")

    print("✓ All containers verified successfully!")
    return True


def main():
    parser = argparse.ArgumentParser(description="Verify a platform release's containers")
    parser.add_argument("version", help="Version to verify (e.g., 1.18.10)")

    args = parser.parse_args()

    if not verify_containers_exist(args.version):
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
