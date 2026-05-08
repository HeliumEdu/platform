__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings

from conf.celery import app
from helium.auth.models import UserPushToken
from helium.common.periodic import PERIODIC_TASKS
from helium.common.services.pushservice import send_notifications
from helium.common.services.sesreputationservice import process_ses_notification
from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


@app.task(bind=True)
def send_pushes(self, push_tokens, username, subject, message, reminder_data):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("push.sent", priority="high", published_at_ms=published_at_ms)

    if settings.DISABLE_PUSH:
        logger.warning(
            f'Push disabled. Push with message "{message}" to {username} not sent.')
        metricutils.task_stop(metrics, value=0)
        return

    invalid_tokens = send_notifications(push_tokens, subject, message, reminder_data)

    if invalid_tokens:
        deleted_count, _ = UserPushToken.objects.filter(token__in=invalid_tokens).delete()
        logger.info(f"Removed {deleted_count} invalid push token(s) after send failure")
        metricutils.increment('action.push.token.purged', value=deleted_count)

    metricutils.task_stop(metrics)


@app.task(bind=True)
def process_ses_event(self, message_json):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("ses.event.processed", priority="low", published_at_ms=published_at_ms)

    process_ses_notification(message_json)

    metricutils.task_stop(metrics)


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):  # pragma: no cover
    for spec in PERIODIC_TASKS:
        sig = spec.task.s()
        if spec.priority is not None:
            sig = sig.set(priority=spec.priority)
        sender.add_periodic_task(spec.schedule, sig)
