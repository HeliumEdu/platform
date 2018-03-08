import logging

from django.conf import settings

from conf.celery import app
from helium.common.services.smsservice import send_sms
from helium.common.utils import metricutils

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.8'

logger = logging.getLogger(__name__)


@app.task
def send_text(phone, message):
    if settings.DISABLE_EMAILS:
        logger.warning(
            'Emails disabled. Text with message "{}" to {} not sent.'.format(message, phone))
        return

    logger.info('Sending text with message "{}" to {}'.format(message, phone))

    send_sms(phone, message)

    metricutils.increment('task.text.sent')
