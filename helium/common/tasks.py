__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging

from django.conf import settings

from conf.celery import app
from helium.auth.models import UserPushToken
from helium.common.services.phoneservice import send_sms
from helium.common.services.pushservice import send_notifications
from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


@app.task(bind=True)
def send_text(self, phone, message):
    published_at_ms = metricutils.get_published_at_ms(self)
    metrics = metricutils.task_start("text.sent", priority="high", published_at_ms=published_at_ms)

    if settings.DISABLE_TEXTS:
        logger.warning(
            f'Texts disabled. Text with message "{message}" to {phone} not sent.')
        metricutils.task_stop(metrics, value=0)
        return

    send_sms(phone, message)
    metricutils.task_stop(metrics)


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
