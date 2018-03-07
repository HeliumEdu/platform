import logging

from django.conf import settings
from twilio.rest import Client

__author__ = "Alex Laird"
__copyright__ = "Copyright 2018, Helium Edu"
__version__ = '1.3.8'

logger = logging.getLogger(__name__)

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_text(phone, message):
    client.api.account.messages.create(
        to=phone,
        from_=settings.TWILIO_SMS_FROM,
        body=message)
