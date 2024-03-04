"""
Settings specific to prod-like deployable code, reading values from system environment variables.
"""

__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import os

from boto.s3.connection import OrdinaryCallingFormat

from conf.configs import common
from conf.settings import PROJECT_ID

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

SERVE_LOCAL = os.environ.get('PROJECT_SERVE_LOCAL', 'False') == 'True'

# Security

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

# Logging

ROLLBAR = {
    'access_token': os.environ.get('PLATFORM_ROLLBAR_POST_SERVER_ITEM_ACCESS_TOKEN'),
    'environment': os.environ.get('ENVIRONMENT'),
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
        'django': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'/var/log/{PROJECT_ID}/django.log',
            'maxBytes': 50000000,
            'backupCount': 3,
            'formatter': 'standard',
        },
        'health_check': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'/var/log/{PROJECT_ID}/health_check.log',
            'maxBytes': 50000000,
            'backupCount': 3,
            'formatter': 'standard',
        },
        'platform_auth': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'/var/log/{PROJECT_ID}/platform_auth.log',
            'maxBytes': 50000000,
            'backupCount': 3,
            'formatter': 'standard',
        },
        'platform_common': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'/var/log/{PROJECT_ID}/platform_common.log',
            'maxBytes': 50000000,
            'backupCount': 3,
            'formatter': 'standard',
        },
        'platform_feed': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'/var/log/{PROJECT_ID}/platform_feed.log',
            'maxBytes': 50000000,
            'backupCount': 3,
            'formatter': 'standard',
        },
        'platform_importexport': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'/var/log/{PROJECT_ID}/platform_importexport.log',
            'maxBytes': 50000000,
            'backupCount': 3,
            'formatter': 'standard',
        },
        'platform_planner': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': f'/var/log/{PROJECT_ID}/platform_planner.log',
            'maxBytes': 50000000,
            'backupCount': 3,
            'formatter': 'standard',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['django', 'rollbar'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['django', 'rollbar'],
            'level': 'ERROR',
            'propagate': False,
        },
        'health-check': {
            'handlers': ['health_check', 'rollbar'],
            'level': 'ERROR',
        },
        'helium.auth': {
            'handlers': ['platform_auth', 'rollbar'],
            'level': 'INFO',
        },
        'helium.common': {
            'handlers': ['platform_common', 'rollbar'],
            'level': 'INFO',
        },
        'helium.feed': {
            'handlers': ['platform_feed', 'rollbar'],
            'level': 'INFO',
        },
        'helium.importexport': {
            'handlers': ['platform_importexport', 'rollbar'],
            'level': 'INFO',
        },
        'helium.planner': {
            'handlers': ['platform_planner', 'rollbar'],
            'level': 'INFO',
        },
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

    common.PIPELINE['CSS_COMPRESSOR'] = None
    common.PIPELINE['JS_COMPRESSOR'] = None
else:
    # Storages
    INSTALLED_APPS += (
        'storages',
    )

    # Static

    STATICFILES_STORAGE = 'conf.storages.S3StaticPipelineStorage'
    AWS_S3_CALLING_FORMAT = OrdinaryCallingFormat()
    AWS_STORAGE_BUCKET_NAME = os.environ.get('PLATFORM_AWS_S3_STATIC_BUCKET_NAME')
    AWS_S3_CUSTOM_DOMAIN = f's3.amazonaws.com/{AWS_STORAGE_BUCKET_NAME}'
    STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/"

    # Media

    DEFAULT_FILE_STORAGE = 'conf.storages.S3MediaPipelineStorage'
    AWS_MEDIA_STORAGE_BUCKET_NAME = os.environ.get('PLATFORM_AWS_S3_MEDIA_BUCKET_NAME')
    AWS_S3_MEDIA_DOMAIN = f's3.amazonaws.com/{AWS_STORAGE_BUCKET_NAME}'
    MEDIA_URL = f"https://{AWS_S3_MEDIA_DOMAIN}/"

# Celery

CELERY_BROKER_URL = os.environ.get('PLATFORM_REDIS_HOST')
CELERY_RESULT_BACKEND = os.environ.get('PLATFORM_REDIS_HOST')
CELERY_TASK_SOFT_TIME_LIMIT = os.environ.get('PLATFORM_REDIS_TASK_TIMEOUT', 60)
