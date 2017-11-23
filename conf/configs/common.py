"""
Common settings for all environments.
"""

import os
import socket

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '0.5.0'

# Define the base working directory of the application
BASE_DIR = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

# ############################
# Project configuration
# ############################

# Project information

PROJECT_NAME = os.environ.get('PROJECT_NAME')
PROJECT_TAGLINE = os.environ.get('PROJECT_TAGLINE')

# Version information

PROJECT_VERSION = '0.5.0'

# AWS S3

AWS_S3_ACCESS_KEY_ID = os.environ.get('PLATFORM_AWS_S3_ACCESS_KEY_ID')
AWS_S3_SECRET_ACCESS_KEY = os.environ.get('PLATFORM_AWS_S3_SECRET_ACCESS_KEY')

#############################
# Default lists for host-specific configurations
#############################

DEFAULT_INSTALLED_APPS = (
    # Django modules
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sitemaps',
    # Third-party modules
    'widget_tweaks',
    'pipeline',
    # Project modules
    'helium.common',
    'helium.users',
    'helium.planner',
)

DEFAULT_MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

DEFAULT_TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',
    'helium.common.handlers.processors.template',
)

#############################
# Django configuration
#############################

# Application definition

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
AUTH_USER_MODEL = 'users.User'
LOGIN_URL = '/login'
LOGOUT_URL = '/logout'
ROOT_URLCONF = 'conf.urls'
WSGI_APPLICATION = 'conf.wsgi.application'

HOSTNAME = socket.gethostname()

# Internationalization

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_THOUSAND_SEPARATOR = True
USE_TZ = True

# Email settings

ADMIN_EMAIL_ADDRESS = 'admin@heliumedu.com'
SERVER_EMAIL = ADMIN_EMAIL_ADDRESS
EMAIL_USE_TLS = True
EMAIL_PORT = os.environ.get('PLATFORM_EMAIL_PORT')
EMAIL_ADDRESS = 'contact@heliumedu.com'
DEFAULT_FROM_EMAIL = PROJECT_NAME + ' <' + EMAIL_ADDRESS + '>'
EMAIL_HOST = os.environ.get('PLATFORM_EMAIL_HOST')

EMAIL_HOST_USER = os.environ.get('PLATFORM_EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('PLATFORM_EMAIL_HOST_PASSWORD')

# Security

SECRET_KEY = os.environ.get('PLATFORM_SECRET_KEY')
CSRF_COOKIE_SECURE = os.environ.get('PLATFORM_CSRF_COOKIE_SECURE', 'True') == 'True'
SESSION_COOKIE_SECURE = os.environ.get('PLATFORM_SESSION_COOKIE_SECURE', 'True') == 'True'
ALLOWED_HOSTS = os.environ.get('PLATFORM_ALLOWED_HOSTS').split(' ')
CSRF_MIDDLEWARE_SECRET = os.environ.get('PLATFORM_CSRF_MIDDLEWARE_SECRET')

# Logging

DEBUG = os.environ.get('PLATFORM_DEBUG', 'False') == 'True'
TEMPLATE_DEBUG = os.environ.get('PLATFORM_TEMPLATE_DEBUG', 'False') == 'True'

# Static files (CSS, JavaScript, Images)

STATIC_ROOT = 'static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)

# Pipelines

PIPELINE = {
    'DISABLE_WRAPPER': True,
    'STYLESHEETS': {
        'base': {
            'source_filenames': (
                ),
            'output_filename': 'css/base_' + PROJECT_VERSION + '.min.css'
        },
    },
    'JAVASCRIPT': {
        'base': {
            'source_filenames': (
            ),
            'output_filename': 'js/base_' + PROJECT_VERSION + '.min.js'
        },
    }
}

# Celery

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
