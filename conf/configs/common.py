"""
Settings common to all deployment methods.
"""

__copyright__ = "Copyright 2024, Helium Edu"
__license__ = "MIT"
__version__ = "1.6.3"

import os
import socket

from corsheaders.defaults import default_headers

from conf.configcache import config
from conf.settings import PROJECT_ID

# ############################
# Project configuration
# ############################

# Project information

PROJECT_NAME = "Helium Student Planner"
PROJECT_TAGLINE = "Lightening Your Course Load"
PROJECT_APP_HOST = config('PROJECT_APP_HOST', 'http://localhost:3000')
PROJECT_API_HOST = config('PROJECT_API_HOST', 'http://localhost:8000')

PROJECT_APP_HOST_STRIPPED = PROJECT_APP_HOST.replace("http://", "").replace("https://", "")
if ":" in PROJECT_APP_HOST_STRIPPED:
    PROJECT_APP_HOST_STRIPPED = PROJECT_APP_HOST_STRIPPED.split(":")[0]

# Version information

PROJECT_VERSION = __version__

# AWS S3

AWS_S3_ACCESS_KEY_ID = config('PLATFORM_AWS_S3_ACCESS_KEY_ID')
AWS_S3_SECRET_ACCESS_KEY = config('PLATFORM_AWS_S3_SECRET_ACCESS_KEY')

# Twilio

TWILIO_ACCOUNT_SID = config('PLATFORM_TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = config('PLATFORM_TWILIO_AUTH_TOKEN')
TWILIO_SMS_FROM = config('PLATFORM_TWILIO_SMS_FROM')

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
    # Third-party modules
    'pipeline',
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
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

AUTH_TOKEN_EXPIRE_FREQUENCY_HOUR = 5

AUTH_TOKEN_TTL_DAYS = 30

FEED_MAX_CACHEABLE_SIZE = 3000000

# Cache feeds for 3 hours
FEED_CACHE_TTL = 60 * 60 * 3
# Refresh cache 10 mins before it expires
FEED_CACHE_REFRESH_TTL = FEED_CACHE_TTL - (60 * 10)

DB_INTEGRITY_RETRIES = 2

DB_INTEGRITY_RETRY_DELAY = 2

REMINDERS_FREQUENCY_SEC = 30

EXTERNAL_CALENDAR_REINDEX_FREQUENCY_SEC = 60

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

SUPPORT_REDIRECT_URL = "https://github.com/HeliumEdu/platform/wiki"
BUG_REPORT_REDIRECT_URL = "https://github.com/HeliumEdu/platform/issues/new?assignees=&labels=bug&projects=&template=bug-report.yml"

# Healthcheck

HEALTHCHECK_CELERY_TIMEOUT = 10

# API configuration

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
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
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema'
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

ADMIN_EMAIL_ADDRESS = 'admin@heliumedu.com'
SERVER_EMAIL = ADMIN_EMAIL_ADDRESS
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_ADDRESS = 'contact@heliumedu.com'
DEFAULT_FROM_EMAIL = f'{PROJECT_NAME} <{EMAIL_ADDRESS}>'
EMAIL_HOST = 'email-smtp.us-east-1.amazonaws.com'

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
ALLOWED_HOSTS = ["localhost", PROJECT_APP_HOST_STRIPPED]
CSRF_TRUSTED_ORIGINS = [PROJECT_APP_HOST, PROJECT_API_HOST]
CORS_ORIGIN_WHITELIST = ["http://localhost:3000", PROJECT_APP_HOST]
CORS_ALLOW_HEADERS = default_headers + (
    'cache-control',
)

# Logging

DEBUG = config('PLATFORM_DEBUG', 'False') == 'True'

# Static files (CSS, JavaScript, Images)

STATIC_ROOT = 'static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)

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

DATADOG_API_KEY = config('PROJECT_DATADOG_API_KEY')
DATADOG_APP_KEY = config('PROJECT_DATADOG_APP_KEY')

# Server

USE_NGROK = config("USE_NGROK", "False") == "True" and os.environ.get("RUN_MAIN", None) != "true"
