import logging

from django.conf import settings

from conf.celery import app
from helium.common.services.phoneservice import send_sms
from helium.common.utils import metricutils

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.38"

logger = logging.getLogger(__name__)


@app.task
def send_text(phone, message):
    if settings.DISABLE_EMAILS:
        logger.warning(
            f'Emails disabled. Text with message "{message}" to {phone} not sent.')
        return

    logger.info(f'Sending text with message "{message}" to {phone}')

    send_sms(phone, message)

    metricutils.increment('task.text.sent')
