import json
import os

import botocore.session
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig

if os.environ.get("PLATFORM_AWS_SECRET_MANAGER_SECRET_NAME"):
    client = botocore.session.get_session().create_client('secretsmanager',
                                                          os.environ.get('PLATFORM_AWS_SECRET_MANAGER_REGION'))
    cache_config = SecretCacheConfig()
    cache = SecretCache(config=cache_config, client=client)
    secret_str = cache.get_secret_string(os.environ.get('PLATFORM_AWS_SECRET_MANAGER_SECRET_NAME'))
    secrets = json.loads(secret_str)
else:
    secrets = os.environ


def get_secret(name, default=None):
    return secrets.get(name, default)
