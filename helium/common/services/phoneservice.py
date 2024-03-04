__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging
import re

from django.conf import settings
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from helium.common.utils.commonutils import HeliumError

logger = logging.getLogger(__name__)


class HeliumPhoneError(HeliumError):
    pass


client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def send_sms(phone, message):
    client.api.account.messages.create(
        to=phone,
        from_=settings.TWILIO_SMS_FROM,
        body=message)


def verify_number(phone):
    try:
        cleaned_phone = re.sub("[()\-+\s]", "", phone)

        logger.info(f"Asking Twilio to validate {cleaned_phone}")

        number = client.lookups.phone_numbers(cleaned_phone).fetch()

        return number.phone_number
    except TwilioRestException:
        raise HeliumPhoneError("Oops, that looks like an invalid phone number.")
