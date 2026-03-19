"""
Initialize Celery with Django configuration.
"""

__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import os
import sys
import time

from django.conf import settings

from celery import Celery
from celery.signals import beat_init, before_task_publish

# Set the default Django settings module for Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')

app = Celery('conf')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@before_task_publish.connect(weak=False)
def add_publish_time(sender=None, headers=None, **kwargs):
    """Add publish timestamp to task headers for queue wait time tracking."""
    if headers is not None:
        published_at = time.time()
        headers['published_at'] = published_at
        # Also add to nested headers dict which becomes self.request.headers on the worker
        if 'headers' in headers and isinstance(headers['headers'], dict):
            headers['headers']['published_at'] = published_at


@beat_init.connect
def on_beat_init(sender, **kwargs):
    """Emit nightly metrics on Beat startup for immediate validation."""
    from helium.auth.tasks import emit_nightly_metrics
    emit_nightly_metrics.delay()


if 'celery' in sys.argv[0]:
    from sentry_sdk.integrations.celery import CeleryIntegration
    import sentry_sdk

    # Initialize Sentry for Celery workers
    sentry_sdk.init(
        dsn=settings.config('PLATFORM_SENTRY_DSN') if hasattr(settings, 'config') else os.environ.get('PLATFORM_SENTRY_DSN'),
        integrations=[CeleryIntegration()],
        environment=settings.ENVIRONMENT if hasattr(settings, 'ENVIRONMENT') else os.environ.get('PLATFORM_ENVIRONMENT', 'production'),
        release=settings.PROJECT_VERSION if hasattr(settings, 'PROJECT_VERSION') else None,
        send_default_pii=False,
        traces_sample_rate=0.1,
    )
