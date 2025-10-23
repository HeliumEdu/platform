#!/usr/bin/env python

import json
import os
import sys
import time

import requests

ENVIRONMENT = os.environ.get("ENVIRONMENT")
TERRAFORM_API_TOKEN = os.environ.get("TERRAFORM_API_TOKEN")
VERSION = 'latest'

if not ENVIRONMENT or not TERRAFORM_API_TOKEN:
    print(
        "ERROR: Set all required env vars: ENVIRONMENT, TERRAFORM_API_TOKEN.")
    sys.exit(1)

INFO_URI = "https://{}.heliumedu.com/info".format("api" if ENVIRONMENT == "prod" else f"api.{ENVIRONMENT}")

# TODO: migrate this Terraform deployment code in to `heliumcli`, then it can be removed from deploy and platform

workspaces_response = requests.get(f"https://app.terraform.io/api/v2/organizations/HeliumEdu/workspaces/{ENVIRONMENT}",
                                   headers={"Authorization": f"Bearer {TERRAFORM_API_TOKEN}",
                                            "Content-Type": "application/vnd.api+json"}).json()

response = requests.post(f"https://app.terraform.io/api/v2/runs",
                         headers={"Authorization": f"Bearer {TERRAFORM_API_TOKEN}",
                                  "Content-Type": "application/vnd.api+json"},
                         data=json.dumps({"data":
                             {"attributes": {
                                 "message": f"[heliumcli] CI deploy {VERSION}",
                                 "allow-empty-apply": "false",
                                 "auto-apply": "true",
                                 "variables": [
                                     {"key": "helium_version", "value": f"\"{VERSION}\""}
                                 ]
                             }, "relationships": {
                                 "workspace": {
                                     "data": {
                                         "id": workspaces_response["data"]["id"],
                                         "type": "workspaces"
                                     }
                                 }
                             }}}).encode()).json()

# In `dev` where we do CI, auto-apply is enabled, so no need to wait for plan here

#####################################################################
# Wait for the Terraform apply to be live
#####################################################################

current_version = None
version_is_live = False
retries = 0
retry_sleep_seconds = 20
wait_minutes = 10
while retries < ((wait_minutes * 60) / retry_sleep_seconds):
    result = requests.get(INFO_URI).json()
    if current_version and result["version"] != current_version:
        version_is_live = True
        break
    else:
        if not current_version:
            current_version = result["version"]

        retries += 1
        print(f"Waiting for {ENVIRONMENT} to report version {VERSION} ...")
        time.sleep(retry_sleep_seconds)

if version_is_live:
    print(f"... {VERSION} is now live in {ENVIRONMENT}.")
else:
    print(
        f"ERROR: {ENVIRONMENT} has not updated its version number to {VERSION} within {wait_minutes} minutes, "
        "check if deploy failed.")
    sys.exit(1)
