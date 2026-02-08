"""
Initialize Celery with Django configuration.
"""

__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.83"

import os
import sys

from django.conf import settings

from celery import Celery

# Set the default Django settings module for Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')

app = Celery('conf')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

if 'celery' in sys.argv[0]:
    from sentry_sdk.integrations.celery import CeleryIntegration
    import sentry_sdk

    # Initialize Sentry for Celery workers
    sentry_sdk.init(
        dsn=settings.config('PLATFORM_SENTRY_DSN') if hasattr(settings, 'config') else os.environ.get('PLATFORM_SENTRY_DSN'),
        integrations=[CeleryIntegration()],
        environment=settings.ENVIRONMENT if hasattr(settings, 'ENVIRONMENT') else os.environ.get('PLATFORM_ENVIRONMENT', 'production'),
        release=settings.PROJECT_VERSION if hasattr(settings, 'PROJECT_VERSION') else None,
        send_default_pii=True,
        traces_sample_rate=0.1,
    )
