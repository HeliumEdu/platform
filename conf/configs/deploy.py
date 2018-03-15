"""
Settings specific to prod-like deployable code, reading values from system environment variables.
"""

import os

from boto.s3.connection import OrdinaryCallingFormat

from .common import DEFAULT_TEMPLATES, DEFAULT_MIDDLEWARE, DEFAULT_INSTALLED_APPS, PROJECT_NAME, ADMIN_EMAIL_ADDRESS, \
    DEBUG, PIPELINE

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.8'

# Define the base working directory of the application
BASE_DIR = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

# Application definition

INSTALLED_APPS = DEFAULT_INSTALLED_APPS

MIDDLEWARE = DEFAULT_MIDDLEWARE

TEMPLATES = DEFAULT_TEMPLATES

if DEBUG:
    TEMPLATES[0]['OPTIONS']['context_processors'] += (
        'django.template.context_processors.debug',
    )

#############################
# Django configuration
#############################

# Project configuration

SERVE_LOCAL = os.environ.get('PROJECT_SERVE_LOCAL', 'False') == 'True'

# Security

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

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
            'filename': '/var/log/helium/django.log',
            'maxBytes': 50000000,
            'backupCount': 3,
            'formatter': 'standard',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
        'platform_common_log': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/helium/platform_common.log',
            'maxBytes': 50000000,
            'backupCount': 3,
            'formatter': 'standard',
        },
        'platform_auth_log': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/helium/platform_auth.log',
            'maxBytes': 50000000,
            'backupCount': 3,
            'formatter': 'standard',
        },
        'platform_planner_log': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/helium/platform_planner.log',
            'maxBytes': 50000000,
            'backupCount': 3,
            'formatter': 'standard',
        },
        'platform_feed_log': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/helium/platform_feed.log',
            'maxBytes': 50000000,
            'backupCount': 3,
            'formatter': 'standard',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['django_log', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'helium.common': {
            'handlers': ['platform_common_log', 'mail_admins'],
            'level': 'INFO',
        },
        'helium.auth': {
            'handlers': ['platform_auth_log', 'mail_admins'],
            'level': 'INFO',
        },
        'helium.planner': {
            'handlers': ['platform_planner_log', 'mail_admins'],
            'level': 'INFO',
        },
        'helium.feed': {
            'handlers': ['platform_feed_log', 'mail_admins'],
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

if SERVE_LOCAL:
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
else:
    # Storages
    INSTALLED_APPS += (
        'storages',
    )

    # Static

    STATICFILES_STORAGE = 'conf.s3storages.S3StaticPipelineStorage'
    AWS_S3_CALLING_FORMAT = OrdinaryCallingFormat()
    AWS_STORAGE_BUCKET_NAME = os.environ.get('PLATFORM_AWS_S3_STATIC_BUCKET_NAME')
    AWS_S3_CUSTOM_DOMAIN = 's3.amazonaws.com/{}'.format(AWS_STORAGE_BUCKET_NAME)
    STATIC_URL = "https://{}/".format(AWS_S3_CUSTOM_DOMAIN)

    # Media

    DEFAULT_FILE_STORAGE = 'conf.s3storages.S3MediaPipelineStorage'
    AWS_MEDIA_STORAGE_BUCKET_NAME = os.environ.get('PLATFORM_AWS_S3_MEDIA_BUCKET_NAME')
    AWS_S3_MEDIA_DOMAIN = 's3.amazonaws.com/{}'.format(AWS_STORAGE_BUCKET_NAME)
    MEDIA_URL = "https://{}/".format(AWS_S3_MEDIA_DOMAIN)

# Celery

CELERY_BROKER_URL = os.environ.get('PLATFORM_REDIS_HOST')
