"""
Settings specific to running tests, reading values from `.env`.
"""

import logging
import os

from .common import DEFAULT_TEMPLATES, DEFAULT_MIDDLEWARE, DEFAULT_INSTALLED_APPS, PIPELINE

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.3'

# Define the base working directory of the application
BASE_DIR = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

# Application definition

INSTALLED_APPS = DEFAULT_INSTALLED_APPS

MIDDLEWARE = DEFAULT_MIDDLEWARE

TEMPLATES = DEFAULT_TEMPLATES

# This is an insecure password hasher, but much faster than what would be used in production
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

# Security

CSRF_MIDDLEWARE_SECRET = None

# Logging

DEBUG = False

if os.environ.get('TEST_DEBUG', 'False') == 'True':
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
else:
    logging.disable(logging.ERROR)

# Cache

if os.environ.get('USE_IN_MEMORY_DB', 'True') == 'True':
    from conf.configs import dev

    CACHES = dev.CACHES
else:
    from conf.configs import deploy

    SESSION_ENGINE = deploy.SESSION_ENGINE
    CACHES = deploy.CACHES

# Database

if os.environ.get('USE_IN_MEMORY_DB', 'True') == 'True':
    from conf.configs import dev

    DATABASES = dev.DATABASES
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

PIPELINE['CSS_COMPRESSOR'] = None
PIPELINE['JS_COMPRESSOR'] = None

# Celery

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# StatsD

STATSD_PORT = 0
