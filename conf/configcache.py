import json
import os

import botocore.session
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig
from decouple import config as decouple_config

secret_manager_secret_name = os.environ.get("PLATFORM_AWS_SECRET_MANAGER_SECRET_NAME")
aws_secrets = {}
if secret_manager_secret_name:
    client = botocore.session.get_session().create_client('secretsmanager',
                                                          'us-east-1')
    cache_config = SecretCacheConfig()
    cache = SecretCache(config=cache_config, client=client)
    secret_str = cache.get_secret_string(secret_manager_secret_name)
    aws_secrets = json.loads(secret_str)


def config(name, default=None):
    if name in aws_secrets:
        return aws_secrets[name]
    else:
        return decouple_config(name, default)
