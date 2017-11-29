"""
Common settings for all environments.
"""

import os
import socket

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

# Define the base working directory of the application
BASE_DIR = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

# ############################
# Project configuration
# ############################

# Project information

PROJECT_NAME = os.environ.get('PROJECT_NAME')
PROJECT_TAGLINE = os.environ.get('PROJECT_TAGLINE')

# Version information

PROJECT_VERSION = __version__

# Special configs

ALLOWED_COLORS = ['#ac725e', '#d06b64', '#f83a22', '#fa573c', '#ff7537', '#ffad46', '#42d692', '#16a765',
                  '#7bd148', '#b3dc6c', '#fad165', '#92e1c0', '#9fe1e7', '#9fc6e7', '#4986e7', '#9a9cff', '#b99aff',
                  '#c2c2c2', '#cabdbf', '#cca6ac', '#f691b2', '#cd74e6', '#a47ae2',
                  '#555']

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

DEFAULT_MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

DEFAULT_TEMPLATES = [{
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
            'helium.common.handlers.processors.template',
        ],
        'debug': os.environ.get('PLATFORM_TEMPLATE_DEBUG', 'False') == 'True'
    },
}]

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

ADMIN_EMAIL_ADDRESS = os.environ.get('PROJECT_ADMIN_EMAIL')
SERVER_EMAIL = ADMIN_EMAIL_ADDRESS
EMAIL_USE_TLS = True
EMAIL_PORT = os.environ.get('PLATFORM_EMAIL_PORT')
EMAIL_ADDRESS = os.environ.get('PROJECT_CONTACT_EMAIL')
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
                'css/vendors/jquery-ui.full.min.css',
                'css/vendors/chosen.css',
                'css/vendors/font-awesome.css',
                'css/vendors/ace-fonts.css',
                'css/vendors/ace.css',
                'css/helium.css',
            ),
            'output_filename': 'css/helium_' + PROJECT_VERSION + '.min.css'
        },
        'base_ie8': {
            'source_filenames': (
                'css/vendors/ace-ie.css',
            ),
            'output_filename': 'css/helium_ie8_' + PROJECT_VERSION + '.min.css'
        }
    },
    'JAVASCRIPT': {
        'base': {
            'source_filenames': (
                'js/vendors/jquery.cookie.js',
                'js/vendors/jquery.ui.touch-punch.min.js',
                'js/vendors/chosen.jquery.js',
                'js/vendors/globalize.js',
                'js/vendors/spin.js',
                'js/vendors/jquery.spin.js',
                'js/helium.js',
                'js/vendors/ace-elements.js',
                'js/vendors/ace.js',
                'js/planner-api.js',
            ),
            'output_filename': 'js/helium_' + PROJECT_VERSION + '.min.js'
        },
        'base_header_js': {
            'source_filenames': (
                'js/vendors/ace-extra.js',
            ),
            'output_filename': 'js/helium_header_' + PROJECT_VERSION + '.min.js',
        },
        'base_ie9_js': {
            'source_filenames': (
                'js/vendors/html5shiv.js',
                'js/vendors/respond.js',
            ),
            'output_filename': 'js/helium_ie9_' + PROJECT_VERSION + '.min.js',
        },
        'jstz_js': {
            'source_filenames': (
                'js/vendors/jstz.js',
            ),
            'output_filename': 'js/helium_jstz.min_' + PROJECT_VERSION + '.js',
        },
    }
}

# Celery

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
