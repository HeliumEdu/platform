"""
Settings common to all deployment methods.
"""

import os
import socket

from corsheaders.defaults import default_headers

from conf.settings import PROJECT_ID

__author__ = "Alex Laird"
__copyright__ = "Copyright 2023, Helium Edu"
__version__ = "1.4.50"

# ############################
# Project configuration
# ############################

# Project information

PROJECT_NAME = os.environ.get('PROJECT_NAME')
PROJECT_TAGLINE = os.environ.get('PROJECT_TAGLINE')
PROJECT_APP_HOST = os.environ.get('PROJECT_APP_HOST')
PROJECT_API_HOST = os.environ.get('PROJECT_API_HOST')

# Version information

PROJECT_VERSION = __version__

# AWS S3

AWS_S3_ACCESS_KEY_ID = os.environ.get('PLATFORM_AWS_S3_ACCESS_KEY_ID')
AWS_S3_SECRET_ACCESS_KEY = os.environ.get('PLATFORM_AWS_S3_SECRET_ACCESS_KEY')

# Twilio

TWILIO_ACCOUNT_SID = os.environ.get('PLATFORM_TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('PLATFORM_TWILIO_AUTH_TOKEN')
TWILIO_SMS_FROM = os.environ.get('PLATFORM_TWILIO_SMS_FROM')

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
    'maintenance_mode',
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
    'maintenance_mode.middleware.MaintenanceModeMiddleware',
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
        'debug': os.environ.get('PLATFORM_TEMPLATE_DEBUG', 'False') == 'True'
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

DB_INTEGRITY_RETRIES = 2

DB_INTEGRITY_RETRY_DELAY = 2

REMINDERS_FREQUENCY_SEC = 30

EXTERNAL_CALENDAR_REINDEX_FREQUENCY_SEC = 600

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

SUPPORT_REDIRECT_URL = os.environ.get('PROJECT_SUPPORT_URL')

# Maintenance mode

MAINTENANCE_MODE_IGNORE_STAFF = os.environ.get('PLATFORM_MAINTENANCE_MODE_IGNORE_STAFF', 'False') == 'True'

MAINTENANCE_MODE_IGNORE_SUPERUSER = os.environ.get('PLATFORM_MAINTENANCE_MODE_IGNORE_SUPERUSER', 'True') == 'True'

MAINTENANCE_MODE_IGNORE_TESTS = True

MAINTENANCE_MODE_IGNORE_URLS = ('^/admin',)

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

DISABLE_EMAILS = os.environ.get('PROJECT_DISABLE_EMAILS', 'False') == 'True'

ADMIN_EMAIL_ADDRESS = os.environ.get('PROJECT_ADMIN_EMAIL')
SERVER_EMAIL = ADMIN_EMAIL_ADDRESS
EMAIL_USE_TLS = True
EMAIL_PORT = os.environ.get('PLATFORM_EMAIL_PORT')
EMAIL_ADDRESS = os.environ.get('PROJECT_CONTACT_EMAIL')
DEFAULT_FROM_EMAIL = f'{PROJECT_NAME} <{EMAIL_ADDRESS}>'
EMAIL_HOST = os.environ.get('PLATFORM_EMAIL_HOST')

EMAIL_HOST_USER = os.environ.get('PLATFORM_EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('PLATFORM_EMAIL_HOST_PASSWORD')

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

SECRET_KEY = os.environ.get('PLATFORM_SECRET_KEY')
CSRF_COOKIE_SECURE = os.environ.get('PLATFORM_CSRF_COOKIE_SECURE', 'True') == 'True'
SESSION_COOKIE_SECURE = os.environ.get('PLATFORM_SESSION_COOKIE_SECURE', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('PLATFORM_ALLOWED_HOSTS').split(' ')
CSRF_MIDDLEWARE_SECRET = os.environ.get('PLATFORM_CSRF_MIDDLEWARE_SECRET')
CORS_ORIGIN_WHITELIST = os.environ.get('PLATFORM_CORS_ORIGIN_WHITELIST').split(' ')
CORS_ALLOW_HEADERS = default_headers + (
    'cache-control',
)

# Logging

DEBUG = os.environ.get('PLATFORM_DEBUG', 'False') == 'True'

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

DATADOG_API_KEY = os.environ.get('PROJECT_DATADOG_API_KEY', None)
DATADOG_APP_KEY = os.environ.get('PROJECT_DATADOG_APP_KEY', None)
