"""
Settings specific to prod-like deployable code, reading values from system environment variables.
"""

__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.17"

import os
import sys

from conf.configcache import config
from conf.configs import common
from conf.configs.common import ENVIRONMENT
from conf.utils import strip_scheme

# Define the base working directory of the application
BASE_DIR = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

# Application definition

INSTALLED_APPS = common.INSTALLED_APPS

MIDDLEWARE = common.MIDDLEWARE + (
    'rollbar.contrib.django.middleware.RollbarNotifierMiddleware',
)

TEMPLATES = common.TEMPLATES

if common.DEBUG:
    TEMPLATES[0]['OPTIONS']['context_processors'] += (
        'django.template.context_processors.debug',
    )

# API configuration

common.REST_FRAMEWORK['EXCEPTION_HANDLER'] = 'rollbar.contrib.django_rest_framework.post_exception_handler'

#############################
# Django configuration
#############################

# Project configuration

SERVE_LOCAL = config('PROJECT_SERVE_LOCAL', 'False') == 'True'

# Security

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

if 'celery' not in sys.argv[0]:
    try:
        from urllib.request import urlopen
        import json

        api_container_name = os.environ.get('PLATFORM_API_CONTAINER_NAME', 'helium_platform_api')

        metadata_uri = os.environ.get('ECS_CONTAINER_METADATA_URI_V4')
        response = urlopen(metadata_uri)
        data = json.loads(response.read().decode('utf-8'))
        private_ips = data['Networks'][0]['IPv4Addresses']
        ALLOWED_HOSTS = common.ALLOWED_HOSTS + private_ips

        print(f"INFO: Added AWS private IP {private_ips} to ALLOWED_HOSTS")
    except Exception as e:
        print("INFO: No AWS IPs added to ALLOWED_HOSTS, ignore if not running on AWS")
else:
    ALLOWED_HOSTS = common.ALLOWED_HOSTS

# Logging

ROLLBAR = {
    'access_token': config('PLATFORM_ROLLBAR_POST_SERVER_ITEM_ACCESS_TOKEN'),
    'environment': ENVIRONMENT,
    'branch': 'main',
    'root': BASE_DIR,
}

if not common.DEBUG:
    ADMINS = (
        (common.PROJECT_NAME, common.ADMIN_EMAIL_ADDRESS),
    )
    MANAGERS = ADMINS

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        }
    },
    'handlers': {
        'rollbar': {
            'level': 'WARN',
            'class': 'rollbar.logger.RollbarHandler',
            'filters': ['require_debug_false'],
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'stream': sys.stdout,
            'formatter': 'standard'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['console', 'rollbar'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'rollbar'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security.DisallowedHost': {
            "handlers": ['console'],
            "propagate": False,
        },
        'health_check': {
            'handlers': ['console', 'rollbar'],
            'level': 'ERROR',
        },
        'helium': {
            'handlers': ['console', 'rollbar'],
            'level': 'INFO',
        }
    }
}

# Cache

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': config('PLATFORM_REDIS_HOST'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    },
}

# Database

DATABASES = {
    'default': {
        'NAME': f'platform_{ENVIRONMENT}',
        'ENGINE': 'django.db.backends.mysql',
        'HOST': config('PLATFORM_DB_HOST'),
        'USER': config('PLATFORM_DB_USER'),
        'PASSWORD': config('PLATFORM_DB_PASSWORD'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

if SERVE_LOCAL:
    # Static

    STATIC_URL = '/static/'
    STATIC_ROOT = os.path.join(BASE_DIR, 'static')
    STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'

    # Media

    MEDIA_URL = '/media/'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

    # Pipelines

    common.PIPELINE['CSS_COMPRESSOR'] = None
    common.PIPELINE['JS_COMPRESSOR'] = None
else:
    # Storages
    INSTALLED_APPS += (
        'storages',
    )

    AWS_S3_ENDPOINT_URL = config('PLATFORM_AWS_S3_ENDPOINT_URL', None)
    S3_ENDPOINT_URL = strip_scheme(AWS_S3_ENDPOINT_URL or 's3.amazonaws.com')
    AWS_S3_REGION_NAME = common.AWS_REGION

    # Static

    STATICFILES_STORAGE = 'conf.storages.S3StaticPipelineStorage'
    AWS_STORAGE_BUCKET_NAME = f'heliumedu.{ENVIRONMENT}.static'
    AWS_S3_CUSTOM_DOMAIN = f'{S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}'
    if 'local' in ENVIRONMENT:
        AWS_S3_URL_PROTOCOL = "http:"
        STATIC_URL = f'{AWS_S3_URL_PROTOCOL}//{AWS_S3_CUSTOM_DOMAIN}/'
    else:
        STATIC_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'

    # Media

    DEFAULT_FILE_STORAGE = 'conf.storages.S3MediaPipelineStorage'
    AWS_MEDIA_STORAGE_BUCKET_NAME = f'heliumedu.{ENVIRONMENT}.media'
    AWS_S3_MEDIA_DOMAIN = None
    MEDIA_URL = None

# Celery

CELERY_BROKER_URL = config('PLATFORM_REDIS_HOST')
CELERY_RESULT_BACKEND = config('PLATFORM_REDIS_HOST')
CELERY_TASK_SOFT_TIME_LIMIT = config('PLATFORM_REDIS_TASK_TIMEOUT', 60)
CELERY_TASK_REINDEX_FEEDS_SOFT_TIME_LIMIT = config('PLATFORM_REDIS_TASK_REINDEX_FEEDS_TIMEOUT', 60 * 5)
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
