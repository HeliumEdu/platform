"""
Settings common to all deployment methods.
"""

__copyright__ = "Copyright (c) 2025, Helium Edu"
__license__ = "MIT"
__version__ = "2.2.30"

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

PROJECT_APP_HOST = config('PROJECT_FLUTTER_APP_HOST', 'http://localhost:8080' if 'local' in ENVIRONMENT else f'https://app.{ENVIRONMENT_PREFIX}heliumedu.com')
PROJECT_API_HOST = config('PROJECT_API_HOST', 'http://localhost:8000' if 'local' in ENVIRONMENT else f'https://api.{ENVIRONMENT_PREFIX}heliumedu.com')
PROJECT_APP_LEGACY_HOST = config('PROJECT_APP_HOST', 'http://localhost:3000' if 'local' in ENVIRONMENT else f'https://www.{ENVIRONMENT_PREFIX}heliumedu.com')

# Version information

PROJECT_VERSION = __version__

FRONTEND_LEGACY_VERSION = config('PLATFORM_FRONTEND_LEGACY_VERSION', "latest")

# AWS S3

AWS_S3_ACCESS_KEY_ID = config('PLATFORM_AWS_S3_ACCESS_KEY_ID')
AWS_S3_SECRET_ACCESS_KEY = config('PLATFORM_AWS_S3_SECRET_ACCESS_KEY')

# Twilio

TWILIO_ACCOUNT_SID = config('PLATFORM_TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = config('PLATFORM_TWILIO_AUTH_TOKEN')
TWILIO_SMS_FROM = config('PLATFORM_TWILIO_SMS_FROM')

# Google Analytics

GA4_MEASUREMENT_ID = config('PLATFORM_GA4_MEASUREMENT_ID', default=None)
GA4_API_SECRET = config('PLATFORM_GA4_API_SECRET', default=None)

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
    # Import first, to override Django's auth commands
    'helium.auth',
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
    # Two-factor authentication
    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'two_factor',
    # Third-party modules
    'pipeline',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'django_filters',
    'django_celery_results',
    'corsheaders',
    # Project modules
    'helium.common',
    'helium.feed',
    'helium.importexport',
    'helium.planner',
)

MIDDLEWARE = (
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
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

REMINDER_WATCHDOG_FREQUENCY_SEC = 60 * 60

FEED_MAX_CACHEABLE_SIZE = 3000000

FEED_CACHE_TTL_SECONDS = 60 * 60 * 3
# Refresh cache before it expires
FEED_CACHE_REFRESH_TTL_SECONDS = FEED_CACHE_TTL_SECONDS - (60 * 10)
REINDEX_FEED_FREQUENCY_SEC = 75
FEED_CONSECUTIVE_FAILURE_THRESHOLD = 10

# How long calendar clients may cache ICS feeds before revalidating (15 minutes).
# ETags still ensure correctness on revalidation; this only reduces server-side
# aggregation query load from high-frequency pollers (e.g. iOS Calendar).
FEED_ICS_MAX_AGE_SECONDS = 60 * 15

RESEND_VERIFICATION_COOLDOWN_SECONDS = 60

DB_INTEGRITY_RETRIES = 2

DB_INTEGRITY_RETRY_DELAY_SECS = 2

# Purge users that never finish setting up their account
UNVERIFIED_USER_TTL_DAYS = 7

# Purge push tokens older than this many days (FCM invalidates tokens after ~60 days of non-use)
PUSH_TOKEN_TTL_DAYS = 90

# Dormant user purge settings
PROCESS_DORMANT_USERS_FREQUENCY_SEC = 60 * 60
DORMANT_USER_THRESHOLD_YEARS = 2
DORMANT_USER_WARNING_DAYS = [30, 14, 7, 1]
# Set to 0 to pause dormant email warnings / account deletions
DORMANT_USER_PURGE_MAX_PER_RUN = 50

# App store review prompt settings
REVIEW_PROMPT_INITIAL_DELAY_DAYS = 21
REVIEW_PROMPT_COOLDOWN_DAYS = 90
REVIEW_PROMPT_MAX_REQUESTED = 5
REVIEW_PROMPT_HOMEWORK_THRESHOLD = 7
REVIEW_PROMPT_RECENT_HOMEWORK_THRESHOLD = 4
REVIEW_PROMPT_RECENT_WINDOW_DAYS = 7

EMAIL_SEND_RATE_PER_SEC = 7

BLACKLIST_REFRESH_TOKEN_DELAY_SECS = 30

# Application definition

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
AUTH_USER_MODEL = 'helium_auth.User'
LOGIN_URL = 'admin:login'
LOGIN_REDIRECT_URL = '/admin/'
LOGOUT_URL = 'admin:logout'
LOGOUT_REDIRECT_URL = '/admin/'
ROOT_URLCONF = 'conf.urls'
WSGI_APPLICATION = 'conf.wsgi.application'

HOSTNAME = socket.gethostname()

SUPPORT_URL = f"https://www.{ENVIRONMENT_PREFIX}heliumedu.com/support" if 'local' not in ENVIRONMENT else "https://www.heliumedu.com/support"
STATUS_URL = f"https://status.{ENVIRONMENT_PREFIX}heliumedu.com" if 'local' not in ENVIRONMENT else f"{PROJECT_API_HOST}/status"

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
    'EXCEPTION_HANDLER': 'helium.common.handlers.exceptions.helium_exception_handler',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'helium.auth.backends.JWTAuthentication',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'helium.common.throttles.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/min',
        'user': '120/min',
        'user_legacy': '300/min',  # TODO: Remove once the legacy frontend (www.heliumedu.com) is retired
        'delete_inactive': '1/min',
        'support_contact': '5/hour',
    },
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

ACCESS_TOKEN_TTL_MINUTES = 5
REFRESH_TOKEN_TTL_DAYS = 14

# TTL values for the legacy frontend that doesn't reliably support token refresh
LEGACY_ACCESS_TOKEN_TTL_MINUTES = 60 * 24 * 7
LEGACY_REFRESH_TOKEN_TTL_DAYS = int(config('PLATFORM_LEGACY_REFRESH_TOKEN_TTL_DAYS', '30'))

if ACCESS_TOKEN_TTL_MINUTES < 3:
    raise ImproperlyConfigured("ACCESS_TOKEN_TTL_MINUTES cannot be less than 3")

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=REFRESH_TOKEN_TTL_DAYS),
    'TOKEN_OBTAIN_SERIALIZER': 'helium.auth.serializers.tokenserializer.TokenObtainSerializer',
    'TOKEN_REFRESH_SERIALIZER': 'helium.auth.serializers.tokenserializer.TokenRefreshSerializer',
    'TOKEN_BLACKLIST_SERIALIZER': 'helium.auth.serializers.tokenserializer.TokenBlacklistSerializer',
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True
}


SPECTACULAR_SETTINGS = {
    'TITLE': f"{PROJECT_NAME} API Documentation",
    'VERSION': PROJECT_VERSION,
    'DESCRIPTION': (
        f"{PROJECT_NAME} is a free, color-coded online student planner for classes, "
        "homework, grades, and notes — the academic calendar built for the way you "
        "actually study. "
        "The API exposes the full set of resources behind the app: class groups "
        "(terms), classes, recurring class schedules, weighted grading categories, "
        "assignments, events, reminders, notes, file attachments, resources, external "
        "calendar feeds (Google Calendar, iCloud, etc.), private iCal subscription "
        "feeds, and full account import/export.\n\n"
        "## Authentication\n\n"
        "POST `{\"username\": \"<your email>\", \"password\": \"<your password>\"}` to "
        "`/auth/token/` to obtain `access` and `refresh` tokens. Send subsequent requests with "
        "the `Authorization: Bearer <access>` header. Rotate the access token via "
        "`/auth/token/refresh/` before it expires; exact lifetimes are published at runtime by "
        "`GET /info/` as `access_token_lifetime_minutes` and `refresh_token_lifetime_days`.\n\n"
        "## Vocabulary (wire format vs. user-facing terms)\n\n"
        f"The wire format keeps some legacy names that differ from what users see in the "
        f"{PROJECT_NAME} App. Each wire name (used in API paths and JSON keys) below "
        f"corresponds to the term displayed in the app.\n\n"
        "| Wire (API) | User-facing | Notes |\n"
        "| --- | --- | --- |\n"
        "| `course_group` | **class group** (semester / quarter / term) | Container for the classes a user is taking in a given period. |\n"
        "| `course` | **class** | A single class within a class group. The API uses `course` to avoid the reserved word `class`. |\n"
        "| `homework` | **assignment** | A graded item for a class. The API uses `homework` to avoid the reserved word `assignment`. |\n"
        "| `material` | **resource** | A reference item (syllabus, textbook, link). `material` is the internal model name surfaced in API paths (`/planner/materials/`) and as the per-homework relation field (`homework.materials`, a list of resource ids). The top-level bulk-import key is `resources` (matching the user-facing term). |\n"
        "| `material_group` | **resource group** | A container for resources. `material_group` appears in API paths (`/planner/materialgroups/`). The top-level bulk-import key is `resource_groups`. |\n\n"
        "Integrations that surface these to end users should use the user-facing terms "
        f"to match the {PROJECT_NAME} App.\n\n"
        "## Importing a schedule from a syllabus\n\n"
        "GET `/auth/user/` first and read `settings.time_zone` (an IANA name like "
        "`America/Los_Angeles`); every `start` / `end` you send needs an offset consistent with "
        "that zone.\n\n"
        "### Bulk import via `/importexport/import/`\n\n"
        "The bulk-import path lets you import many resources in one atomic call rather than N "
        "individual POSTs — more efficient for large batches, equivalent results otherwise. "
        "Produce a single JSON file matching the `Export` component schema (the same shape returned by "
        "`GET /importexport/export/`) and upload it as a multipart form field named `file[]` to "
        "`POST /importexport/import/`. The benefits:\n\n"
        "- One atomic call, no token-expiry exposure mid-import.\n"
        "- Predictable shape — every relationship is expressed as an integer `id` within the same "
        "file, so there is no GET-then-POST dance.\n"
        "- Forward-compatibility shims (e.g. legacy reminder types) are applied in one place.\n\n"
        "The `Export` schema in this document is the canonical bulk-import target — its keys "
        "(`course_groups`, `courses`, `course_schedules`, `categories`, `homework`, `events`, "
        "`reminders`, `notes`, `resources`, `resource_groups`, `external_calendars`) and per-row "
        "fields are exactly what the importer accepts. See the `bulk_syllabus_import` example on "
        "the `/importexport/import/` operation for a trimmed payload.\n\n"
        "Each `CourseSchedule` has 14 day-time fields (`sun_start_time`, `sun_end_time`, ... "
        "`sat_end_time`). Omitted day-times default to `12:00:00`, which may collide with real "
        "classes. **Send `00:00:00` for off-days** to make the schedule unambiguous.\n\n"
        "### Incremental edits via REST\n\n"
        "POST in this order so each create succeeds:\n\n"
        "1. `POST /planner/coursegroups/` — the term (semester / quarter).\n"
        "2. `POST /planner/coursegroups/{course_group}/courses/` — each class within the term. "
        "Use `\"0.00\"` for `credits` when the syllabus is silent, rather than guessing. "
        "Capture any university holidays or instruction-pattern overrides in `Course.exceptions` "
        "(`YYYYMMDD` CSV).\n"
        "3. (Optional) `POST /planner/coursegroups/{course_group}/courses/{course}/courseschedules/` — "
        "recurring weekly meeting times for the class (at most one schedule per class).\n"
        "4. (Optional) `POST /planner/coursegroups/{course_group}/courses/{course}/categories/` — graded "
        "categories such as Homework, Exams. Sum of `weight` across a class's categories must stay <= 100. "
        "Set `weight=0` on every category for syllabi using total points rather than weighted "
        "percentages; `current_grade` fractions then carry the points and `Course.has_weighted_grading` "
        "reports `false` in that mode. An `Uncategorized` category is auto-created on demand if you "
        "create homework without one.\n"
        "5. `POST /planner/coursegroups/{course_group}/courses/{course}/homework/` — individual assignments. "
        "Set `current_grade` to `\"-1/100\"` for ungraded items.\n"
        "6. (Optional) `POST /planner/events/` — non-class calendar items (study sessions, office hours). "
        "Events have no Course dependency.\n"
        "7. (Optional) `POST /planner/reminders/` — push/email reminders attached to exactly one parent "
        "(`event`, `homework`, or `course`).\n"
        "8. (Optional) `POST /planner/notes/`, `POST /planner/attachments/` — rich-text notes and file "
        "uploads linked to a single parent entity each.\n\n"
        "### Common pitfalls\n\n"
        "A few shapes that return 2xx but produce semantically wrong data:\n\n"
        "- **Off-day times default to `12:00:00`.** Send `00:00:00` for both `_start_time` and "
        "`_end_time` on every day a class does NOT meet, so the off-day is unambiguous. Omitted "
        "day-times default to `12:00:00`, which collides with real classes meeting at noon.\n"
        "- **One CourseSchedule per Course.** A schedule supports a different start and end time on "
        "each day of the week, so a class that meets MWF at 10:00 and Thursdays at 14:00 fits "
        "cleanly in one schedule. Use separate Courses (e.g. `\"BIO 151 — Lecture\"` and "
        "`\"BIO 151 — Lab\"`) for sections with distinct rooms, TAs, or grading rubrics — "
        "alternating-week patterns and same-weekday two-block patterns are common cases that "
        "fall under this rule. The API rejects a second schedule on a Course.\n"
        "- **Biweekly CourseSchedule meetings.** Helium has no biweekly CourseSchedule recurrence — use `Course.exceptions` "
        "(`YYYYMMDD` CSV) to skip every alternate week from a normal weekly schedule.\n"
        "- **No recurrence on Homework or Events.** A weekly problem set across a 15-week term must be "
        "15 separate Homework rows; a weekly office-hour Event likewise. Three ways to handle this:\n"
        "  1. Enumerate the rows up front and POST each one.\n"
        "  2. Use the bulk-import path — one JSON file, one call (more efficient for large batches).\n"
        "  3. Create a canonical row and use the clone endpoints "
        "(`POST /planner/coursegroups/{cg}/courses/{c}/homework/{id}/clone/` or "
        "`POST /planner/events/{id}/clone/`, both with no body) to duplicate it for incremental "
        "additions mid-term — clones copy reminders too — then PATCH each clone with its new "
        "`start` / `end`. This is what the Flutter client does.\n"
        "- **No multi-part assignment grouping.** A `\"draft + final\"` or `\"post + reply\"` pair is "
        "two independent Homework rows with descriptive titles (`\"Essay 1 — Draft\"`, "
        "`\"Essay 1 — Final\"`). Helium has no parent/child or group concept for assignments.\n"
        "- **Idempotency.** Helium does not enforce uniqueness on title for CourseGroups or "
        "Courses — duplicates are valid. Always reference an existing entity by its `id`, never by its "
        "title alone. GET `/planner/coursegroups/` (and the nested Course list) before a re-import "
        "and reuse the existing `id` for any entity you intend to keep; titles are display names, "
        "not identifiers."
    ),
    'CONTACT': {
        'name': f'{PROJECT_NAME} Support',
        'url': SUPPORT_URL,
    },
    'LICENSE': {
        'name': 'MIT',
        'url': 'https://opensource.org/licenses/MIT',
    },
    'SERVERS': [
        {
            'url': PROJECT_API_HOST,
            'description': f'{PROJECT_NAME} API' + (f' ({ENVIRONMENT})' if 'prod' not in ENVIRONMENT else ''),
        },
    ],
    'SERVE_INCLUDE_SCHEMA': False,
    'SORT_OPERATIONS': True,
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.hooks.postprocess_schema_enums',
        'helium.common.utils.openapiutils.add_tag_groups',
        'helium.common.utils.openapiutils.strip_enum_int_bounds',
    ],
    'ENUM_NAME_OVERRIDES': {
        'ReminderOffsetTypeEnum': enums.REMINDER_OFFSET_TYPE_CHOICES,
        'ReminderTypeEnum': enums.REMINDER_TYPE_CHOICES,
    },
    'TAGS': [
        {
            'name': 'planner.homework',
            'description': (
                'Graded calendar items — assignments, quizzes, exams. Tied to a class and '
                'a category; `current_grade` rolls up into class and class-group grades. '
                'Ungraded calendar items live under `Event`. See '
                'https://www.heliumedu.com/support/grades-and-progress/setting-up-weighted-grading-assignment-categories for more info on grading.'
            ),
        },
        {
            'name': 'planner.event',
            'description': (
                'Ungraded calendar items not tied to a class. Anything graded '
                '(assignments, quizzes, exams) lives under `Homework`. See '
                'https://www.heliumedu.com/support/grades-and-progress/how-helium-calculates-your-grades'
            ),
        },
    ],
}

# Internationalization

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_THOUSAND_SEPARATOR = True
USE_TZ = True

# DateTime sanity

NORMALIZED_DATE_FORMAT = '%a, %b %d'
NORMALIZED_DATE_TIME_FORMAT = f'{NORMALIZED_DATE_FORMAT} at %I:%M %p'

# File uploads

FILE_TYPES = ['json']

MAX_UPLOAD_SIZE = 10485760

BLOCKED_ATTACHMENT_EXTENSIONS = {
    '.php', '.php3', '.php4', '.php5', '.phtml',
    '.pyc', '.rb', '.pl',
    '.sh', '.bash', '.zsh', '.fish',
    '.ps1', '.psm1', '.psd1',
    '.bat', '.cmd', '.com',
    '.exe', '.dll', '.so', '.dylib',
}

BLOCKED_ATTACHMENT_MIME_TYPES = {
    'application/x-httpd-php', 'application/x-php',
    'application/x-sh', 'application/x-shellscript',
    'application/x-msdownload', 'application/x-executable',
}

# Email settings

DISABLE_EMAILS = config('PROJECT_DISABLE_EMAILS', 'False') == 'True'
DISABLE_TEXTS = config('PROJECT_DISABLE_TEXTS', 'False') == 'True'
DISABLE_PUSH = config('PROJECT_DISABLE_PUSH', 'False') == 'True'

REMINDER_SEND_WINDOW_MINUTES = int(config('PROJECT_REMINDER_SEND_WINDOW_MINUTES', '15'))

ADMIN_EMAIL_ADDRESS = f'support@{ENVIRONMENT_PREFIX}heliumedu.com'
SERVER_EMAIL = ADMIN_EMAIL_ADDRESS
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_ADDRESS = f'contact@{ENVIRONMENT_PREFIX}heliumedu.com'
DEFAULT_FROM_EMAIL = f'{PROJECT_NAME} <{EMAIL_ADDRESS}>'
EMAIL_HOST = config('PLATFORM_EMAIL_HOST', f'email-smtp.{AWS_REGION}.amazonaws.com')

EMAIL_HOST_USER = config('PLATFORM_EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('PLATFORM_EMAIL_HOST_PASSWORD')
SES_CONFIGURATION_SET = f'helium-{ENVIRONMENT}'

SES_COMPLAINT_SUPPRESS_THRESHOLD = int(config('PLATFORM_SES_COMPLAINT_SUPPRESS_THRESHOLD', '2'))

SES_SNS_TOPIC_ARN = config('PLATFORM_SES_SNS_TOPIC_ARN', '')

SUPPORT_INBOX_EMAIL = config('PLATFORM_SUPPORT_INBOX_EMAIL', 'support@heliumedu.atlassian.net')

# Authentication

AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.AllowAllUsersModelBackend']

ADMIN_ALLOWED_DOMAINS = [d.strip() for d in config('ADMIN_ALLOWED_DOMAINS', default='heliumedu.com').split(',')]

ADMIN_ENFORCE_2FA = (config('PLATFORM_ADMIN_ENFORCE_2FA', default=None) or ('False' if 'local' in ENVIRONMENT else 'True')) == 'True'

TWO_FACTOR_PATCH_ADMIN = False

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
CSRF_COOKIE_SECURE = 'local' not in ENVIRONMENT
SESSION_COOKIE_SECURE = 'local' not in ENVIRONMENT
ALLOWED_HOSTS = [
    urlparse(PROJECT_API_HOST).netloc.split(':')[0]
]
PROJECT_CI_APP_HOST = config('PROJECT_CI_APP_HOST', None)

PROJECT_LANDING_HOST = config(
    'PROJECT_LANDING_HOST',
    'http://localhost:4321' if 'local' in ENVIRONMENT else f'https://landing.{ENVIRONMENT_PREFIX}heliumedu.com'
)

CSRF_TRUSTED_ORIGINS = [
    PROJECT_APP_HOST,
    PROJECT_API_HOST,
    PROJECT_APP_LEGACY_HOST,
    strip_www(PROJECT_APP_LEGACY_HOST),
    PROJECT_LANDING_HOST,
]
CORS_ALLOWED_ORIGINS = [
    PROJECT_APP_HOST,
    PROJECT_API_HOST,
    PROJECT_APP_LEGACY_HOST,
    strip_www(PROJECT_APP_LEGACY_HOST),
    PROJECT_LANDING_HOST,
]

if PROJECT_CI_APP_HOST:
    CSRF_TRUSTED_ORIGINS.append(PROJECT_CI_APP_HOST)
    CORS_ALLOWED_ORIGINS.append(PROJECT_CI_APP_HOST)
CORS_ALLOWED_ORIGIN_REGEXES = []
CORS_ALLOW_HEADERS = default_headers + (
    'cache-control',
    'sentry-trace',
    'baggage',
    'traceparent',
    'tracestate',
    'x-client-version',
    'x-client-platform',
    'x-request-id',
)

if 'prod' not in ENVIRONMENT:
    CSRF_TRUSTED_ORIGINS += [
        'http://localhost:8080',
        'http://127.0.0.1:8080',
        # Legacy frontend
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ]
    CORS_ALLOWED_ORIGINS += [
        'http://localhost:8080',
        'http://127.0.0.1:8080',
        # Legacy frontend
        'http://localhost:3000',
        'http://127.0.0.1:3000',
    ]

if 'local' in ENVIRONMENT:
    ALLOWED_HOSTS += [
        'localhost',
        '127.0.0.1',
        '.ngrok.dev',
    ]
    CSRF_TRUSTED_ORIGINS += [
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'https://*.ngrok.dev',
    ]
    CORS_ALLOWED_ORIGINS += [
        'http://localhost:8000',
        'http://127.0.0.1:8000',
    ]
    CORS_ALLOWED_ORIGIN_REGEXES += [
        r"https://\w+\.ngrok\.dev"
    ]

# Logging

DEBUG = config('PLATFORM_DEBUG', 'False') == 'True'

SILENCED_SYSTEM_CHECKS = [
    'fields.W342',  # ForeignKey(unique=True) on CourseSchedule.course; intentional, not converting to OneToOneField
]

if 'prod' in ENVIRONMENT and DEBUG:
    raise ImproperlyConfigured("DEBUG must not be enabled in production environments")

# Static files (CSS, JavaScript, Images)

STATIC_ROOT = 'static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)

# Celery

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

CELERY_RESULT_BACKEND = 'django-db'
CELERY_RESULT_EXTENDED = True
CELERY_RESULT_EXPIRES = 3600 * 24 * 7

# Priority constants for Celery tasks (lower number = higher priority)
CELERY_PRIORITY_HIGH = 0
CELERY_PRIORITY_LOW = 9

# Soft time limits for long-running tasks (None = no limit; overridden per environment)
CELERY_TASK_REINDEX_FEEDS_SOFT_TIME_LIMIT = None

# Enable priority support in Redis broker
CELERY_BROKER_TRANSPORT_OPTIONS = {
    'priority_steps': list(range(10)),
    'queue_order_strategy': 'priority',
}

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

SENTRY_ENABLED = False

# Server

USE_NGROK = config("USE_NGROK", "false").lower() == "true" and os.environ.get("RUN_MAIN", None) != "true"
