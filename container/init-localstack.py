import json
import os

import boto3

s3_client = boto3.client(
    "s3",
    endpoint_url=f"http://localhost:4566",
    aws_access_key_id="test",
    aws_secret_access_key="test"
)

s3_client.create_bucket(Bucket="heliumedu.dev.static")
s3_client.create_bucket(Bucket="heliumedu.dev.media")
