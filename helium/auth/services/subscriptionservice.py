import logging

from django.contrib.auth import get_user_model

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def process_unsubscribe(username, code):
    try:
        user = get_user_model().objects.get(username=username, verification_code=code)

        user.settings.receive_emails_from_admin = False

        user.settings.save()

        return True
    except get_user_model().DoesNotExist:
        pass

    return False
