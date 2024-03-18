"""
Settings specific to running tests, reading values from `.env`.
"""

__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.6.0"

import logging
import os

from conf.configs import common

# Define the base working directory of the application
BASE_DIR = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

# Application definition

INSTALLED_APPS = common.INSTALLED_APPS

MIDDLEWARE = common.MIDDLEWARE

TEMPLATES = common.TEMPLATES

# This is an insecure password hasher, but much faster than what would be used in production
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

# Logging

DEBUG = False

if os.environ.get('TEST_LOGGING', 'False') == 'True':
    from conf.configs import dev

    LOGGING = dev.LOGGING
else:
    logging.disable(logging.ERROR)

# Cache

if os.environ.get('USE_IN_MEMORY_CACHE', 'True') == 'True':
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

common.PIPELINE['CSS_COMPRESSOR'] = None
common.PIPELINE['JS_COMPRESSOR'] = None

# Celery

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# StatsD

STATSD_PORT = 0
