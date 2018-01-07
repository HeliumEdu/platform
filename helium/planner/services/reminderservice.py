import logging

import pytz
from django.conf import settings
from django.utils import timezone

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


def get_subject(reminder):
    timezone.activate(pytz.timezone(reminder.user.settings.time_zone))

    if reminder.homework:
        calendar_item = reminder.homework
        subject = '{} in {}'.format(calendar_item.title, calendar_item.course.title)
    elif reminder.event:
        calendar_item = reminder.event
        subject = calendar_item.title
    else:
        return

    start = timezone.localtime(calendar_item.start).strftime(
        settings.NORMALIZED_DATE_FORMAT if calendar_item.all_day else settings.NORMALIZED_DATE_TIME_FORMAT)
    subject += ' on {}'.format(start)

    return subject
