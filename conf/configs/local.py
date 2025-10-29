"""
Settings specific to a development environment using Django's `runserver` command, reading values from `.env`.
"""

__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.15.15"

import os
import warnings

from conf.configcache import config
from conf.configs import common
from conf.configs.common import PROJECT_NAME

# Define the base working directory of the application
BASE_DIR = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

# Application definition

INSTALLED_APPS = common.INSTALLED_APPS + (
    'debug_toolbar',
)

MIDDLEWARE = common.MIDDLEWARE + (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

TEMPLATES = common.TEMPLATES

TEMPLATES[0]['OPTIONS']['context_processors'] += (
    'django.template.context_processors.debug',
)

#############################
# Django configuration
#############################

# Project configuration

SERVE_LOCAL = config('PROJECT_SERVE_LOCAL', 'True') == 'True'

# Email settings

EMAIL_ADDRESS = f'contact@dev-local.heliumedu.com'
DEFAULT_FROM_EMAIL = f'{PROJECT_NAME} <{EMAIL_ADDRESS}>'

# Security

INTERNAL_IPS = (
    '127.0.0.1',
)

ALLOWED_HOSTS = common.ALLOWED_HOSTS

CSRF_TRUSTED_ORIGINS = common.CSRF_TRUSTED_ORIGINS

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
        'health-check': {
            'handlers': ['console'],
            'level': 'ERROR',
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

if config('USE_IN_MEMORY_CACHE', 'True') == 'True':
    CACHES = {
        'default': {
            'BACKEND': 'helium.common.cache.locmemkeys.LocMemKeysCache',
            'LOCATION': 'unique-snowflake',
        }
    }
else:
    from conf.configs import deploy

    SESSION_ENGINE = deploy.SESSION_ENGINE
    CACHES = deploy.CACHES

# Database

if config('USE_IN_MEMORY_DB', 'True') == 'True':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        }
    }
else:
    from conf.configs import deploy

    DATABASES = deploy.DATABASES

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

# Celery

if config('USE_IN_MEMORY_WORKER', 'True') == 'True':
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True
    CELERY_TASK_REINDEX_FEEDS_SOFT_TIME_LIMIT = 15
else:
    from conf.configs import deploy

    CELERY_BROKER_URL = deploy.CELERY_BROKER_URL
    CELERY_TASK_SOFT_TIME_LIMIT = deploy.CELERY_TASK_SOFT_TIME_LIMIT
    CELERY_TASK_REINDEX_FEEDS_SOFT_TIME_LIMIT = deploy.CELERY_TASK_REINDEX_FEEDS_SOFT_TIME_LIMIT
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = deploy.CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP
