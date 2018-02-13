"""
Settings common to all deployment methods.
"""

import os
import socket

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.4'

# Define the base working directory of the application
BASE_DIR = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', '..'))

# ############################
# Project configuration
# ############################

# Project information

PROJECT_NAME = os.environ.get('PROJECT_NAME')
PROJECT_TAGLINE = os.environ.get('PROJECT_TAGLINE')
PLATFORM_HOST = os.environ.get('PLATFORM_HOST')

# Version information

PROJECT_VERSION = __version__

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
    'maintenance_mode',
    'widget_tweaks',
    'pipeline',
    'rest_framework',
    'django_filters',
    # Project modules
    'helium.common',
    'helium.auth',
    'helium.planner',
    'helium.feed',
    'helium.importexport',
)

DEFAULT_MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'maintenance_mode.middleware.MaintenanceModeMiddleware',
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

# Project configuration

SERVE_LOCAL = False

# Application definition

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
AUTH_USER_MODEL = 'helium_auth.User'
LOGIN_URL = '/login'
LOGIN_REDIRECT_URL = '/planner'
LOGOUT_URL = '/logout'
ROOT_URLCONF = 'conf.urls'
WSGI_APPLICATION = 'conf.wsgi.application'

HOSTNAME = socket.gethostname()

SUPPORT_REDIRECT_URL = 'https://heliumedu.uservoice.com'

# Maintenance mode

MAINTENANCE_MODE_IGNORE_STAFF = os.environ.get('PLATFORM_MAINTENANCE_MODE_IGNORE_STAFF', 'False') == 'True'

MAINTENANCE_MODE_IGNORE_SUPERUSER = os.environ.get('PLATFORM_MAINTENANCE_MODE_IGNORE_SUPERUSER', 'True') == 'True'

MAINTENANCE_MODE_IGNORE_TESTS = True

MAINTENANCE_MODE_IGNORE_URLS = (
    '^/admin', '^/$', '^/support', '^/terms', '^/privacy', '^/press', '^/about', '^/contact')

MAINTENANCE_MODE_TEMPLATE = os.environ.get('PLATFORM_MAINTENANCE_MODE_TEMPLATE', 'errors/maintenance.html')

# API configuration

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/min',
        'user': '1000/min'
    },
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',)
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
NORMALIZED_DATE_TIME_FORMAT = '{} at %I:%M %p'.format(NORMALIZED_DATE_FORMAT)

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
DEFAULT_FROM_EMAIL = '{} <{}>'.format(PROJECT_NAME, EMAIL_ADDRESS)
EMAIL_HOST = os.environ.get('PLATFORM_EMAIL_HOST')

EMAIL_HOST_USER = os.environ.get('PLATFORM_EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('PLATFORM_EMAIL_HOST_PASSWORD')

# Authentication

AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.AllowAllUsersModelBackend']

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

# Media files

MEDIA_ROOT = 'media/'

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
            'output_filename': 'css/helium_{}.min.css'.format(PROJECT_VERSION)
        },
        'base_ie8': {
            'source_filenames': (
                'css/vendors/ace-ie.css',
            ),
            'output_filename': 'css/helium_ie8_{}.min.css'.format(PROJECT_VERSION)
        },
        'settings_pre': {
            'source_filenames': (
                'css/vendors/bootstrap-editable.css',
                'css/vendors/jquery.simplecolorpicker.css',
                'css/vendors/jquery.simplecolorpicker-glyphicons.css',
            ),
            'output_filename': 'css/helium_settings_pre_{}.min.css'.format(PROJECT_VERSION),
        },
        'settings': {
            'source_filenames': (
                'css/settings.css',
            ),
            'output_filename': 'css/helium_settings_{}.min.css'.format(PROJECT_VERSION),
        },
        'calendar_pre': {
            'source_filenames': (
                'css/vendors/bootstrap-editable.css',
                'css/vendors/fullcalendar.css',
                'css/vendors/datepicker.css',
                'css/vendors/bootstrap-timepicker.css',
                'css/vendors/jquery.simplecolorpicker.css',
                'css/vendors/jquery.simplecolorpicker-glyphicons.css',
                'css/vendors/dropzone.css',
                'css/vendors/jquery.qtip.css',
            ),
            'output_filename': 'css/helium_calendar_pre_{}.min.css'.format(PROJECT_VERSION),
        },
        'calendar_print': {
            'source_filenames': (
                'css/vendors/fullcalendar.print.css',
            ),
            'output_filename': 'css/helium_calendar_print_{}.min.css'.format(PROJECT_VERSION),
            'extra_context': {
                'media': 'print',
            },
        },
        'calendar': {
            'source_filenames': (
                'css/calendar.css',
            ),
            'output_filename': 'css/helium_calendar_post_{}.min.css'.format(PROJECT_VERSION),
        },
        'classes_pre': {
            'source_filenames': (
                'css/vendors/bootstrap-editable.css',
                'css/vendors/typeahead.js-bootstrap.css',
                'css/vendors/datepicker.css',
                'css/vendors/bootstrap-timepicker.css',
                'css/vendors/jquery.simplecolorpicker.css',
                'css/vendors/jquery.simplecolorpicker-glyphicons.css',
                'css/vendors/dropzone.css',
            ),
            'output_filename': 'css/helium_classes_pre_{}.min.css'.format(PROJECT_VERSION),
        },
        'classes': {
            'source_filenames': (
                'css/classes.css',
            ),
            'output_filename': 'css/helium_classes_{}.min.css'.format(PROJECT_VERSION),
        },
        'materials_pre': {
            'source_filenames': (
                'css/vendors/bootstrap-editable.css',
            ),
            'output_filename': 'css/helium_materials_pre_{}.min.css'.format(PROJECT_VERSION),
        },
        'materials': {
            'source_filenames': (
                'css/materials.css',
            ),
            'output_filename': 'css/helium_materials_{}.min.css'.format(PROJECT_VERSION),
        },
        'grades_pre': {
            'source_filenames': (
                'css/grades.css',
            ),
            'output_filename': 'css/helium_grades_pre_{}.min.css'.format(PROJECT_VERSION),
        },
    },
    'JAVASCRIPT': {
        'base': {
            'source_filenames': (
                'js/vendors/moment.js',
                'js/vendors/moment-timezone.js',
                'js/vendors/js.cookie.js',
                'js/vendors/jquery.ui.touch-punch.min.js',
                'js/vendors/chosen.jquery.js',
                'js/vendors/spin.js',
                'js/vendors/jquery.spin.js',
                'js/helium.js',
                'js/vendors/ace-elements.js',
                'js/vendors/ace.js',
                'js/planner-api.js',
            ),
            'output_filename': 'js/helium_{}.min.js'.format(PROJECT_VERSION)
        },
        'base_header': {
            'source_filenames': (
                'js/vendors/ace-extra.js',
            ),
            'output_filename': 'js/helium_header_{}.min.js'.format(PROJECT_VERSION)
        },
        'base_ie9': {
            'source_filenames': (
                'js/vendors/html5shiv.js',
                'js/vendors/respond.js',
            ),
            'output_filename': 'js/helium_ie9_{}'.format(PROJECT_VERSION)
        },
        'settings': {
            'source_filenames': (
                'js/vendors/bootstrap-editable.js',
                'js/vendors/jquery.simplecolorpicker.js',
                'js/vendors/bootbox.js',
                'js/settings/main.js',
            ),
            'output_filename': 'js/helium_settings_{}.min.js'.format(PROJECT_VERSION),
        },
        'calendar': {
            'source_filenames': (
                'js/vendors/bootstrap-datepicker.js',
                'js/vendors/bootstrap-timepicker.js',
                'js/vendors/bootstrap-editable.js',
                'js/vendors/bootbox.js',
                'js/vendors/jquery.dataTables.js',
                'js/vendors/jquery.dataTables.bootstrap.js',
                'js/vendors/fullcalendar.js',
                'js/vendors/dropzone.js',
                'js/vendors/jquery.qtip.js',
                'js/vendors/jquery.hotkeys.js',
                'js/vendors/bootstrap-wysiwyg.js',
                'js/calendar/main.js',
                'js/calendar/triggers.js',
            ),
            'output_filename': 'js/helium_calendar_{}.min.js'.format(PROJECT_VERSION),
        },
        'classes': {
            'source_filenames': (
                'js/vendors/bootstrap-datepicker.js',
                'js/vendors/bootstrap-timepicker.js',
                'js/vendors/bootstrap-editable.js',
                'js/vendors/typeahead.js',
                'js/vendors/typeaheadjs.js',
                'js/vendors/bootbox.js',
                'js/vendors/jquery.dataTables.js',
                'js/vendors/jquery.dataTables.bootstrap.js',
                'js/vendors/jquery.simplecolorpicker.js',
                'js/vendors/dropzone.js',
                'js/classes/main.js',
                'js/classes/triggers.js',
            ),
            'output_filename': 'js/helium_classes_{}.min.js'.format(PROJECT_VERSION),
        },
        'materials': {
            'source_filenames': (
                'js/vendors/bootstrap-editable.js',
                'js/vendors/bootbox.js',
                'js/vendors/jquery.dataTables.js',
                'js/vendors/jquery.dataTables.bootstrap.js',
                'js/vendors/jquery.hotkeys.js',
                'js/vendors/bootstrap-wysiwyg.js',
                'js/materials/main.js',
                'js/materials/triggers.js',
            ),
            'output_filename': 'js/helium_materials_{}.min.js'.format(PROJECT_VERSION),
        },
        'grades': {
            'source_filenames': (
                'js/vendors/bootbox.js',
                'js/vendors/jquery.easy-pie-chart.js',
                'js/vendors/jquery.sparkline.js',
                'js/vendors/jquery.flot.js',
                'js/vendors/jquery.flot.pie.js',
                'js/vendors/jquery.flot.resize.js',
                'js/vendors/jquery.flot.time.js',
                'js/grades/main.js',
            ),
            'output_filename': 'js/helium_grades_{}.min.js'.format(PROJECT_VERSION),
        },
    }
}
