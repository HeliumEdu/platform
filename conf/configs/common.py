"""
Settings common to all deployment methods.
"""

__copyright__ = "Copyright (c) 2025, Helium Edu"
__license__ = "MIT"
__version__ = "1.17.44"

import os
import socket
from datetime import timedelta
from urllib.parse import urlparse

from corsheaders.defaults import default_headers
from django.core.exceptions import ImproperlyConfigured

from conf.configcache import config
from conf.settings import PROJECT_ID
from conf.utils import strip_www
from helium.common import enums

# ############################
# Project configuration
# ############################

# Project information

ENVIRONMENT = config('ENVIRONMENT').lower()
ENVIRONMENT_PREFIX = f'{ENVIRONMENT}.' if 'prod' not in ENVIRONMENT else ''

AWS_REGION = config('AWS_REGION', 'us-east-1')

PROJECT_NAME = 'Helium'
PROJECT_TAGLINE = 'Student Planner & Academic Calendar App'

PROJECT_APP_HOST = config('PROJECT_APP_HOST', 'http://localhost:3000' if 'local' in ENVIRONMENT else f'https://www.{ENVIRONMENT_PREFIX}heliumedu.com')
PROJECT_API_HOST = config('PROJECT_API_HOST', 'http://localhost:8000' if 'local' in ENVIRONMENT else f'https://api.{ENVIRONMENT_PREFIX}heliumedu.com')

# Version information

PROJECT_VERSION = __version__

# AWS S3

AWS_S3_ACCESS_KEY_ID = config('PLATFORM_AWS_S3_ACCESS_KEY_ID')
AWS_S3_SECRET_ACCESS_KEY = config('PLATFORM_AWS_S3_SECRET_ACCESS_KEY')

# Twilio

TWILIO_ACCOUNT_SID = config('PLATFORM_TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = config('PLATFORM_TWILIO_AUTH_TOKEN')
TWILIO_SMS_FROM = config('PLATFORM_TWILIO_SMS_FROM')

# Firebase

FIREBASE_CREDENTIALS = {
    'type': 'service_account',
    'project_id': config('PLATFORM_FIREBASE_PROJECT_ID'),
    'private_key_id': config('PLATFORM_FIREBASE_PRIVATE_KEY_ID'),
    'private_key': config('PLATFORM_FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
    'client_email': config('PLATFORM_FIREBASE_CLIENT_EMAIL'),
    'client_id': config('PLATFORM_FIREBASE_CLIENT_ID'),
    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
    'token_uri': 'https://oauth2.googleapis.com/token',
    'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
    'client_x509_cert_url': config('PLATFORM_FIREBASE_CLIENT_X509_CERT_URL'),
    'universe_domain': 'googleapis.com'
} if config('PLATFORM_FIREBASE_PROJECT_ID') else None

#############################
# Default lists for host-specific configurations
#############################

INSTALLED_APPS = (
    # Django modules
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    # Health modules
    'health_check',
    'health_check.db',
    'health_check.cache',
    'health_check.contrib.celery',
    'health_check.contrib.s3boto3_storage',
    # Third-party modules
    'pipeline',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'drf_spectacular_sidecar',
    'django_filters',
    'django_celery_results',
    'corsheaders',
    # Project modules
    'helium.auth',
    'helium.common',
    'helium.feed',
    'helium.importexport',
    'helium.planner',
)

MIDDLEWARE = (
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'helium.common.middleware.exceptionmetric.HeliumExceptionMiddleware',
)

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.contrib.auth.context_processors.auth',
            'django.template.context_processors.media',
            'django.template.context_processors.static',
            'django.template.context_processors.tz',
            'django.contrib.messages.context_processors.messages',
            'django.template.context_processors.request',
        ],
        'debug': config('PLATFORM_TEMPLATE_DEBUG', 'False') == 'True'
    },
}]

#############################
# Django configuration
#############################

# Project configuration

SERVE_LOCAL = False

REFRESH_TOKEN_PURGE_FREQUENCY_SEC = 60 * 60

FEED_MAX_CACHEABLE_SIZE = 3000000

FEED_CACHE_TTL_SECONDS = 60 * 60 * 3
# Refresh cache before it expires
FEED_CACHE_REFRESH_TTL_SECONDS = FEED_CACHE_TTL_SECONDS - (60 * 10)
REINDEX_FEED_FREQUENCY_SEC = 75

DB_INTEGRITY_RETRIES = 2

DB_INTEGRITY_RETRY_DELAY_SECS = 2

REMINDERS_FREQUENCY_SEC = 60

PURGE_UNVERIFIED_USERS_FREQUENCY_SEC = 60 * 60 * 12
# Purge users that never finish setting up their account
UNVERIFIED_USER_TTL_DAYS = 7

BLACKLIST_REFRESH_TOKEN_DELAY_SECS = 30

# Application definition

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
AUTH_USER_MODEL = 'helium_auth.User'
LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/docs'
LOGOUT_URL = '/logout'
LOGOUT_REDIRECT_URL = '/docs'
ROOT_URLCONF = 'conf.urls'
WSGI_APPLICATION = 'conf.wsgi.application'

HOSTNAME = socket.gethostname()

SUPPORT_URL = f"https://support.{ENVIRONMENT_PREFIX}.heliumedu.com" if 'local' not in ENVIRONMENT else "https://support.heliumedu.com"
STATUS_URL = f"https://status.{ENVIRONMENT_PREFIX}.heliumedu.com" if 'local' not in ENVIRONMENT else f"{PROJECT_API_HOST}/status"

# Healthcheck

HEALTH_CHECK = {
    "SUBSETS": {
        "core": ["Database", "Cache", "Storage"],
        "db": ["Database"],
        "cache": ["Cache"],
        "storage": ["Storage"],
        "task-processing": ["TaskProcessing", "CeleryBeat"],
    },
}

HEALTHCHECK_CELERY_TIMEOUT = 10

# API configuration

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/min',
        'user': '1000/min'
    },
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

#ACCESS_TOKEN_TTL_MINUTES = int(config('PLATFORM_ACCESS_TOKEN_TTL_MINUTES', '16'))
# TODO: this is a temporary increase until we fix the frontend issue causing sporadic forced logouts
ACCESS_TOKEN_TTL_MINUTES = 60 * 24 * 7
ACCESS_TOKEN_TTL_DAYS = int(config('PLATFORM_ACCESS_TOKEN_TTL_DAYS', '30'))

if ACCESS_TOKEN_TTL_MINUTES < 3:
    raise ImproperlyConfigured("ACCESS_TOKEN_TTL_MINUTES cannot be less than 3")

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=ACCESS_TOKEN_TTL_DAYS),
    'TOKEN_OBTAIN_SERIALIZER': 'helium.auth.serializers.tokenserializer.TokenObtainSerializer',
    'TOKEN_REFRESH_SERIALIZER': 'helium.auth.serializers.tokenserializer.TokenRefreshSerializer',
    'TOKEN_BLACKLIST_SERIALIZER': 'helium.auth.serializers.tokenserializer.TokenBlacklistSerializer',
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True
}

SPECTACULAR_SETTINGS = {
    'TITLE': "Helium API Documentation",
    'VERSION': PROJECT_VERSION,
    'SERVE_INCLUDE_SCHEMA': False,
    'SWAGGER_UI_DIST': 'SIDECAR',
    'SWAGGER_UI_FAVICON_HREF': 'SIDECAR',
    'ENUM_NAME_OVERRIDES': {
        'ReminderOffsetTypeEnum': enums.REMINDER_OFFSET_TYPE_CHOICES,
        'ReminderTypeEnum': enums.REMINDER_TYPE_CHOICES,
    }
}

# Internationalization

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_THOUSAND_SEPARATOR = True
USE_TZ = True

# DateTime sanity

NORMALIZED_DATE_FORMAT = '%a, %b %d'
NORMALIZED_DATE_TIME_FORMAT = f'{NORMALIZED_DATE_FORMAT} at %I:%M %p'

# File uploads

FILE_TYPES = ['json']

MAX_UPLOAD_SIZE = 10485760

# Email settings

DISABLE_EMAILS = config('PROJECT_DISABLE_EMAILS', 'False') == 'True'
DISABLE_TEXTS = config('PROJECT_DISABLE_TEXTS', 'False') == 'True'
DISABLE_PUSH = config('PROJECT_DISABLE_PUSH', 'False') == 'True'

ADMIN_EMAIL_ADDRESS = f'support@{ENVIRONMENT_PREFIX}heliumedu.com'
SERVER_EMAIL = ADMIN_EMAIL_ADDRESS
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_ADDRESS = f'contact@{ENVIRONMENT_PREFIX}heliumedu.com'
DEFAULT_FROM_EMAIL = f'{PROJECT_NAME} <{EMAIL_ADDRESS}>'
EMAIL_HOST = config('PLATFORM_EMAIL_HOST', f'email-smtp.{AWS_REGION}.amazonaws.com')

EMAIL_HOST_USER = config('PLATFORM_EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('PLATFORM_EMAIL_HOST_PASSWORD')

# Authentication

AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.AllowAllUsersModelBackend']

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Security

SECRET_KEY = config('PLATFORM_SECRET_KEY')
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    '10.0.2.2',
    urlparse(PROJECT_API_HOST).netloc.split(':')[0]
]
CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:3000',
    PROJECT_APP_HOST,
    strip_www(PROJECT_APP_HOST),
    PROJECT_API_HOST
]
CORS_ALLOWED_ORIGINS = [
    'http://127.0.0.1:3000',
    PROJECT_APP_HOST,
    strip_www(PROJECT_APP_HOST),
    PROJECT_API_HOST
]
CORS_ALLOW_HEADERS = default_headers + (
    'cache-control',
)

if 'local' in ENVIRONMENT:
    ALLOWED_HOSTS += [
        '.ngrok.dev'
    ]
    CSRF_TRUSTED_ORIGINS += [
        'https://*.ngrok.dev'
    ]
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r"https://\w+\.ngrok\.dev"
    ]

# Logging

DEBUG = config('PLATFORM_DEBUG', 'False') == 'True'

# Static files (CSS, JavaScript, Images)

STATIC_ROOT = 'static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)

# Celery

CELERY_RESULT_BACKEND = 'django-db'
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_EXPIRES = 3600 * 24 * 7

# Media files

MEDIA_ROOT = 'media/'

# Pipelines

PIPELINE = {
    'DISABLE_WRAPPER': True,
    'STYLESHEETS': {
        'error': {
            'source_filenames': (
                'css/error.css',
            ),
            'output_filename': f'css/{PROJECT_ID}_error_{PROJECT_VERSION}.min.css',
        },
    },
}

# Metrics

DATADOG_STATSD_HOST = config('PROJECT_DATADOG_STATSD_HOST', 'localhost')

# Server

USE_NGROK = config("USE_NGROK", "false").lower() == "true" and os.environ.get("RUN_MAIN", None) != "true"
