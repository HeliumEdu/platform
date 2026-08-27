"""
Initialize Celery with Django configuration.
"""

import os
import time

from django.conf import settings

from celery import Celery
from celery.signals import beat_init, before_task_publish, task_postrun, task_prerun

from helium.common.utils.requestid import get_request_id, reset_request_id, set_request_id

# Set the default Django settings module for Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'conf.settings')

_REQUEST_ID_HEADER = 'request_id'

app = Celery('conf', task_cls='helium.common.utils.taskutils:MetricsTask')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Per-worker-thread reset tokens for the request-id contextvar, keyed by task id.
_request_id_tokens = {}


@before_task_publish.connect(weak=False)
def add_publish_time(sender=None, headers=None, **kwargs):
    """Add publish timestamp to task headers for queue wait time tracking."""
    if headers is not None:
        published_at = time.time()
        headers['published_at'] = published_at
        # Also add to nested headers dict which becomes self.request.headers on the worker
        if 'headers' in headers and isinstance(headers['headers'], dict):
            headers['headers']['published_at'] = published_at


@before_task_publish.connect(weak=False)
def propagate_request_id(sender=None, headers=None, **kwargs):
    """Carry the publisher's request id into task headers so worker logs stay
    correlated with the originating request."""
    request_id = get_request_id()
    if headers is not None and request_id is not None:
        headers[_REQUEST_ID_HEADER] = request_id
        if 'headers' in headers and isinstance(headers['headers'], dict):
            headers['headers'][_REQUEST_ID_HEADER] = request_id


@task_prerun.connect(weak=False)
def bind_request_id(sender=None, task_id=None, task=None, **kwargs):
    """Bind the propagated request id (if any) to the worker context and Sentry
    scope for the duration of the task."""
    request = getattr(task, 'request', None)
    task_headers = getattr(request, 'headers', None) or {}
    request_id = task_headers.get(_REQUEST_ID_HEADER)
    if request_id is None:
        return

    _request_id_tokens[task_id] = set_request_id(request_id)

    if getattr(settings, 'SENTRY_ENABLED', False):
        import sentry_sdk

        sentry_sdk.set_tag('request_id', request_id)


@task_postrun.connect(weak=False)
def unbind_request_id(sender=None, task_id=None, **kwargs):
    """Reset the request-id contextvar bound in :func:`bind_request_id`."""
    token = _request_id_tokens.pop(task_id, None)
    if token is not None:
        reset_request_id(token)


@beat_init.connect
def on_beat_init(sender, **kwargs):
    """Emit nightly metrics on Beat startup for immediate validation."""
    # Use send_task to avoid import issues before Django is fully ready
    app.send_task('helium.auth.tasks.emit_nightly_metrics')
