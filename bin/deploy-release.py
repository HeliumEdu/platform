#!/usr/bin/env python3

"""
Deploy a platform release to an environment.

This script handles the full deployment workflow:
1. Verify containers exist in ECR
2. Update Terraform variables in deploy repo
3. Commit and push changes
4. Find and apply the Terraform plan
5. Wait for deployment to complete
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests
from git import Repo


def verify_containers_exist(version, aws_region="us-east-1"):
    """Verify that all platform containers exist in ECR for the given version."""
    print(f"Verifying containers exist for version {version}...")

    containers = ["platform-resource", "platform-api", "platform-worker"]

    for container in containers:
        print(f"  Checking {container}:amd64-{version}...")

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


def update_terraform_variables(deploy_repo_path, environment, version):
    """Update the helium_version variable in Terraform."""
    print(f"Updating Terraform variables for {environment} to version {version}...")

    variables_file = Path(deploy_repo_path) / "terraform" / "environments" / environment / "variables.tf"

    if not variables_file.exists():
        print(f"✗ Variables file not found: {variables_file}")
        return False

    # Read the file
    with open(variables_file, 'r') as f:
        content = f.read()

    # Update only the helium_version variable's default value using awk-like logic
    lines = content.split('\n')
    new_lines = []
    in_helium_version_block = False

    for line in lines:
        if line.strip().startswith('variable "helium_version"'):
            in_helium_version_block = True
            new_lines.append(line)
        elif in_helium_version_block and 'default' in line:
            # Replace the default value
            new_line = re.sub(
                r'default\s*=\s*"[^"]*"',
                f'default     = "{version}"',
                line
            )
            new_lines.append(new_line)
            in_helium_version_block = False
        else:
            new_lines.append(line)

    # Write back
    with open(variables_file, 'w') as f:
        f.write('\n'.join(new_lines))

    print(f"✓ Updated {variables_file} with version {version}")

    # Show the updated variable
    print("\nhelium_version variable:")
    subprocess.run(["grep", "-A", "2", 'variable "helium_version"', str(variables_file)])

    return True


def commit_and_push_changes(deploy_repo_path, version, environment):
    """Commit and push Terraform changes.

    Returns:
        tuple: (success: bool, changes_pushed: bool)
            - (True, True) if changes were pushed successfully
            - (True, False) if no changes needed (already up to date)
            - (False, False) if an error occurred
    """
    print(f"\nCommitting and pushing changes...")

    repo = Repo(deploy_repo_path)
    origin = repo.remote('origin')

    print(f"Remote 'origin' URL: {origin.url}")
    print("Pulling latest changes from origin...")
    origin.pull('main')

    # Check if there are changes
    if not repo.is_dirty(untracked_files=False):
        print("✓ No changes to commit - version already deployed")
        return (True, False)  # Success, but no changes

    # Stage the variables file
    variables_file = f"terraform/environments/{environment}/variables.tf"
    repo.index.add([variables_file])

    # Commit with [platform] prefix so Terraform run is identifiable
    commit_message = f"[platform] Deploy {version} to {environment}"
    repo.index.commit(commit_message)

    # Create and push tag
    tag_name = f"v{version}"
    if tag_name not in repo.tags:
        repo.create_tag(tag_name, message=f"Release {tag_name}")

    # Push
    try:
        print("Pushing to origin...")

        # Push main branch
        push_info = origin.push('main')
        for info in push_info:
            if info.flags & info.ERROR:
                print(f"✗ Push failed: {info.summary}")
                return (False, False)
            if info.flags & info.REJECTED:
                print(f"✗ Push rejected: {info.summary}")
                return (False, False)

        # Push tag
        tag_push_info = origin.push(tag_name)
        for info in tag_push_info:
            if info.flags & info.ERROR:
                print(f"✗ Tag push failed: {info.summary}")
                return (False, False)
            if info.flags & info.REJECTED:
                print(f"✗ Tag push rejected: {info.summary}")
                return (False, False)

        print(f"✓ Committed and pushed: {commit_message}")
    except Exception as e:
        print(f"✗ Push failed with exception: {e}")
        return (False, False)

    return (True, True)  # Success with changes pushed


def find_and_apply_terraform_run(environment, version, terraform_token, timeout_minutes=6):
    """Find the Terraform run for this deployment and apply it."""
    print(f"\nFinding and applying Terraform run...")

    headers = {
        "Authorization": f"Bearer {terraform_token}",
        "Content-Type": "application/vnd.api+json"
    }

    # Get workspace details
    workspace_resp = requests.get(
        f"https://app.terraform.io/api/v2/organizations/HeliumEdu/workspaces/{environment}",
        headers=headers
    )
    workspace_resp.raise_for_status()
    workspace_id = workspace_resp.json()['data']['id']

    print(f"Workspace ID: {workspace_id}")

    # Wait for and find the [platform] run, discard competing runs
    print(f"Waiting for [platform] Terraform plan for version {version}...")

    iterations = (timeout_minutes * 60) // 10
    run_id = None

    for i in range(iterations):
        time.sleep(10)

        # Get runs
        runs_resp = requests.get(
            f"https://app.terraform.io/api/v2/workspaces/{workspace_id}/runs",
            headers=headers
        )
        runs_resp.raise_for_status()
        runs = runs_resp.json()

        # Discard competing runs
        for run in runs.get('data', []):
            run_id_iter = run['id']
            status = run['attributes']['status']
            message = run['attributes'].get('message', '')

            # Discard non-[platform] planned/pending runs or wrong version
            if status in ['planned', 'pending'] and \
               (not message.startswith('[platform]') or version not in message):

                actions = run['attributes'].get('actions', {})
                reject_endpoint = 'cancel' if actions.get('is-cancelable') else 'discard'

                print(f"  Discarding run {run_id_iter}: {message}")
                requests.post(
                    f"https://app.terraform.io/api/v2/runs/{run_id_iter}/actions/{reject_endpoint}",
                    headers=headers,
                    json={"comment": "Discarding in favor of official [platform] release"}
                )

        # Find our [platform] run
        for run in runs.get('data', []):
            status = run['attributes']['status']
            message = run['attributes'].get('message', '')

            if status == 'planned' and message.startswith('[platform]') and version in message:
                run_id = run['id']
                break

        if run_id:
            print(f"✓ Found [platform] run {run_id} for version {version}")
            break

    if not run_id:
        print(f"✗ No [platform] planned run found within {timeout_minutes} minutes")
        return False

    # Apply the plan
    print(f"Applying Terraform plan {run_id}...")
    apply_resp = requests.post(
        f"https://app.terraform.io/api/v2/runs/{run_id}/actions/apply",
        headers=headers,
        json={"comment": f"[platform] Apply {version}"}
    )

    if apply_resp.status_code not in [200, 202]:
        print(f"✗ Apply failed with HTTP {apply_resp.status_code}")
        print(f"Response: {apply_resp.text}")
        return False

    print("✓ Apply triggered successfully")
    return True


def wait_for_deployment(environment, version, timeout_minutes=10):
    """Wait for the platform API to report the new version."""
    print(f"\nWaiting for deployment to be live...")

    if environment == "prod":
        info_uri = "https://api.heliumedu.com/info"
    else:
        info_uri = f"https://api.{environment}.heliumedu.com/info"

    print(f"Checking {info_uri} for version {version}...")

    iterations = (timeout_minutes * 60) // 20

    for i in range(iterations):
        time.sleep(20)

        try:
            response = requests.get(info_uri, timeout=10)
            if response.status_code == 200:
                data = response.json()
                current_version = data.get('version', 'unknown')

                print(f"  Current version: {current_version} (waiting for {version})")

                if current_version == version:
                    print(f"✓ Version {version} is now live in {environment}!")
                    return True
            else:
                print(f"  API returned HTTP {response.status_code}")
        except Exception as e:
            print(f"  API error: {e}")

    print(f"✗ Deployment did not complete within {timeout_minutes} minutes")
    return False


def main():
    parser = argparse.ArgumentParser(description="Deploy platform release")
    parser.add_argument("version", help="Version to deploy (e.g., 1.18.10)")
    parser.add_argument("environment", choices=["dev", "prod"], help="Environment to deploy to")
    parser.add_argument("--deploy-repo", required=True, help="Path to deploy repository")
    parser.add_argument("--skip-verify", action="store_true", help="Skip container verification")
    parser.add_argument("--skip-wait", action="store_true", help="Skip waiting for deployment")

    args = parser.parse_args()

    print(f"Starting deployment of version {args.version} to {args.environment}...")
    print(f"Deploy repo: {args.deploy_repo}")
    print(f"Skip verify: {args.skip_verify}, Skip wait: {args.skip_wait}\n")

    # Get required environment variables
    terraform_token = os.environ.get('TERRAFORM_API_TOKEN')
    if not terraform_token:
        print("✗ TERRAFORM_API_TOKEN environment variable required")
        return 1

    # Verify containers exist
    if not args.skip_verify:
        if not verify_containers_exist(args.version):
            return 1

    # Update Terraform variables
    if not update_terraform_variables(args.deploy_repo, args.environment, args.version):
        return 1

    # Commit and push
    success, changes_pushed = commit_and_push_changes(args.deploy_repo, args.version, args.environment)
    if not success:
        return 1

    # Find and apply Terraform run (only if changes were pushed)
    if changes_pushed:
        if not find_and_apply_terraform_run(args.environment, args.version, terraform_token):
            return 1
    else:
        print("\nSkipping Terraform apply - no changes were pushed")

    # Wait for deployment
    if not args.skip_wait:
        if not wait_for_deployment(args.environment, args.version):
            return 1

    print(f"\n✓ Deployment complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
