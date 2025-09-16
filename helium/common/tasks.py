__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from django.conf import settings

from conf.celery import app
from helium.common.services import phoneservice, pushservice
from helium.common.utils import metricutils

logger = logging.getLogger(__name__)


@app.task
def send_text(phone, message):
    if settings.DISABLE_TEXTS:
        logger.warning(
            f'Texts disabled. Text with message "{message}" to {phone} not sent.')
        return

    logger.info(f'Sending text with message "{message}" to {phone}')

    phoneservice.send_text(phone, message)

    metricutils.increment('task.text.sent')


@app.task
def send_push(push_tokens, username, subject, message):
    if settings.DISABLE_PUSH:
        logger.warning(
            f'Push disabled. Push with message "{message}" to {username} not sent.')
        return

    logger.info(f'Sending push with message "{message}" to {username}')

    pushservice.send_push(push_tokens, subject, message)

    metricutils.increment('task.push.sent')
