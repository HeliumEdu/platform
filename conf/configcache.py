import json
import os

import botocore.session
from aws_secretsmanager_caching import SecretCache, SecretCacheConfig
from decouple import config as decouple_config

use_aws_secrets_manager = os.environ.get('USE_AWS_SECRETS_MANAGER', 'False') == 'True'
aws_secrets = {}
if use_aws_secrets_manager:
    client = botocore.session.get_session().create_client('secretsmanager',
                                                          os.environ.get("AWS_REGION"))
    cache_config = SecretCacheConfig()
    cache = SecretCache(config=cache_config, client=client)
    environ = decouple_config('ENVIRONMENT').lower()
    secret_str = cache.get_secret_string(f'{environ}/helium')
    aws_secrets = json.loads(secret_str)


def config(name, default=None):
    if name in aws_secrets:
        return aws_secrets[name]
    else:
        return decouple_config(name, default)
