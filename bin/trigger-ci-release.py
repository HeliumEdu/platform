#!/usr/bin/env python

import json
import os
import sys

import requests

ENVIRONMENT = os.environ.get("ENVIRONMENT")
TERRAFORM_API_TOKEN = os.environ.get("TERRAFORM_API_TOKEN")
VERSION = 'latest'

if not ENVIRONMENT or not TERRAFORM_API_TOKEN:
    print(
        "ERROR: Set all required env vars: ENVIRONMENT, TERRAFORM_API_TOKEN.")
    sys.exit(1)

# TODO: migrate this Terraform deployment code in to `heliumcli`, then it can be removed from deploy and platform

workspaces_response = requests.get(f"https://app.terraform.io/api/v2/organizations/HeliumEdu/workspaces/{ENVIRONMENT}",
                                   headers={"Authorization": f"Bearer {TERRAFORM_API_TOKEN}",
                                            "Content-Type": "application/vnd.api+json"}).json()

response = requests.post(f"https://app.terraform.io/api/v2/runs",
                         headers={"Authorization": f"Bearer {TERRAFORM_API_TOKEN}",
                                  "Content-Type": "application/vnd.api+json"},
                         data=json.dumps({"data":
                             {"attributes": {
                                 "message": f"[heliumcli] Deploy {VERSION}",
                                 "allow-empty-apply": "true",
                                 "auto-apply": "false",
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
