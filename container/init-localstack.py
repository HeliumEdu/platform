import os

import boto3

s3_client = boto3.client(
    "s3",
    endpoint_url=f"http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test"
)

ENVIRONMENT = os.environ.get("ENVIRONMENT").lower()

s3_client.create_bucket(Bucket=f"heliumedu.{ENVIRONMENT}.static")
s3_client.create_bucket(Bucket=f"heliumedu.{ENVIRONMENT}.media")
