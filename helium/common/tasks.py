__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.5"

import logging

from django.conf import settings

from conf.celery import app
from helium.common.services.phoneservice import send_sms
from helium.common.services.pushservice import send_notifications
from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


@app.task
def send_text(phone, message):
    if settings.DISABLE_TEXTS:
        logger.warning(
            f'Texts disabled. Text with message "{message}" to {phone} not sent.')
        return

    send_sms(phone, message)

    metricutils.increment('task.text.sent')


@app.task
def send_pushes(push_tokens, username, subject, message):
    if settings.DISABLE_PUSH:
        logger.warning(
            f'Push disabled. Push with message "{message}" to {username} not sent.')
        return

    send_notifications(push_tokens, subject, message)

    metricutils.increment('task.push.sent')
