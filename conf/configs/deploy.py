"""
Settings for a stable, prod-ready environment. Data is loaded from environment variables, so no sensitive information is
stored in this file.
"""

import os

from boto.s3.connection import OrdinaryCallingFormat

from .common import DEFAULT_TEMPLATES, DEFAULT_MIDDLEWARE, DEFAULT_INSTALLED_APPS, \
    PROJECT_NAME, ADMIN_EMAIL_ADDRESS, DEBUG

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

# Define the base working directory of the application
BASE_DIR = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

# Application definition

INSTALLED_APPS = DEFAULT_INSTALLED_APPS + (
    'storages',
)

MIDDLEWARE = DEFAULT_MIDDLEWARE

TEMPLATES = DEFAULT_TEMPLATES

if DEBUG:
    TEMPLATES[0]['OPTIONS']['context_processors'] += (
        'django.template.context_processors.debug',
    )

#############################
# Django configuration
#############################

# Application configuration

PREPEND_WWW = os.environ.get('PLATFORM_PREPEND_WWW', 'False') == 'True'

# Security

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = "default"

# Logging

if not DEBUG:
    ADMINS = (
        (PROJECT_NAME, ADMIN_EMAIL_ADDRESS),
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
    'handlers': {
        'django_log': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/' + PROJECT_NAME.lower() + '/django.log',
            'maxBytes': 50000000,
            'backupCount': 3,
            'formatter': 'standard',
        },
        'platform_users_log': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/' + PROJECT_NAME.lower() + '/platform_users.log',
            'maxBytes': 50000000,
            'backupCount': 3,
            'formatter': 'standard',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['django_log', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'helium.users': {
            'handlers': ['platform_users_log', 'mail_admins'],
            'level': 'INFO',
        }
    }
}

# Cache

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('PLATFORM_REDIS_HOST'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    },
}

# Database

DATABASES = {
    'default': {
        'NAME': os.environ.get('PLATFORM_DB_NAME'),
        'ENGINE': 'django.db.backends.mysql',
        'HOST': os.environ.get('PLATFORM_DB_HOST'),
        'USER': os.environ.get('PLATFORM_DB_USER'),
        'PASSWORD': os.environ.get('PLATFORM_DB_PASSWORD'),
    }
}

# Static

STATICFILES_STORAGE = 'conf.s3storages.S3PipelineManifestStorage'
AWS_S3_CALLING_FORMAT = OrdinaryCallingFormat()
AWS_STORAGE_BUCKET_NAME = os.environ.get('PLATFORM_AWS_S3_STATIC_BUCKET_NAME')
AWS_S3_CUSTOM_DOMAIN = 's3.amazonaws.com/{}'.format(AWS_STORAGE_BUCKET_NAME)
STATIC_URL = "https://{}/static".format(AWS_S3_CUSTOM_DOMAIN)
MEDIA_URL = "https://{}/media".format(AWS_S3_CUSTOM_DOMAIN)

# Celery

BROKER_URL = os.environ.get('PLATFORM_REDIS_HOST')
FANOUT_PREFIX = True
FANOUT_PATTERNS = True
VISIBILITY_TIMEOUT = 43200
