"""
Settings for a development environment when using Django's `runserver` command.
"""

import os
import warnings

from . import deploy
from .common import DEFAULT_MIDDLEWARE, DEFAULT_INSTALLED_APPS, PIPELINE, DEFAULT_TEMPLATES

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

# Define the base working directory of the application
BASE_DIR = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

# Application definition

INSTALLED_APPS = DEFAULT_INSTALLED_APPS + (
    'debug_toolbar',
)

MIDDLEWARE = DEFAULT_MIDDLEWARE + (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

TEMPLATES = DEFAULT_TEMPLATES

TEMPLATES[0]['OPTIONS']['context_processors'] += (
    'django.template.context_processors.debug',
)

#############################
# Django configuration
#############################

# Security

INTERNAL_IPS = (
    '127.0.0.1',
)

# Logging

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'standard'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'propagate': True,
            'level': 'WARN',
        },
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'helium': {
            'handlers': ['console'],
            'level': 'DEBUG',
        }
    }
}

# When in development, we want to be warned about dates that don't have a timezone
warnings.filterwarnings('error', r"DateTimeField .* received a naive datetime", RuntimeWarning,
                        r'django\.db\.models\.fields')

# Cache

if os.environ.get('USE_IN_MEMORY_CACHE', 'True') != 'True':
    SESSION_ENGINE = deploy.SESSION_ENGINE
    SESSION_CACHE_ALIAS = deploy.SESSION_CACHE_ALIAS

    CACHES = deploy.CACHES

# Database

if os.environ.get('USE_IN_MEMORY_DB', 'True') == 'True':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else:
    DATABASES = deploy.DATABASES

# Static

if os.environ.get('USE_LOCAL_STATIC', 'True') == 'True':
    STATIC_URL = '/static/'
    STATICFILES_STORAGE = 'pipeline.storage.PipelineStorage'

    # Pipelines

    PIPELINE['CSS_COMPRESSOR'] = None
    PIPELINE['JS_COMPRESSOR'] = None
else:
    INSTALLED_APPS += (
        'storages',
    )

    AWS_S3_CALLING_FORMAT = deploy.AWS_S3_CALLING_FORMAT
    AWS_STORAGE_BUCKET_NAME = deploy.AWS_STORAGE_BUCKET_NAME
    AWS_S3_CUSTOM_DOMAIN = deploy.AWS_S3_CUSTOM_DOMAIN
    STATIC_URL = deploy.STATIC_URL
    STATICFILES_STORAGE = deploy.STATICFILES_STORAGE

# Celery

if os.environ.get('USE_IN_MEMORY_CACHE', 'True') != 'True':
    BROKER_URL = deploy.BROKER_URL
    FANOUT_PREFIX = deploy.FANOUT_PREFIX
    FANOUT_PATTERNS = deploy.FANOUT_PATTERNS
    VISIBILITY_TIMEOUT = deploy.VISIBILITY_TIMEOUT
else:
    CELERY_ALWAYS_EAGER = True
    CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
