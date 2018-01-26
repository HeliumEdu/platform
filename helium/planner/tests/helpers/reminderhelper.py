import datetime

from dateutil import parser
from django.utils import timezone

from helium.common import enums
from helium.planner.models import Reminder

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


def given_reminder_exists(user, title='Test Reminder', message='You need to do something now.', offset=15,
                          offset_type=enums.MINUTES, type=enums.TEXT, sent=False, from_admin=False, event=None,
                          homework=None):
    reminder = Reminder.objects.create(title=title,
                                       message=message,
                                       offset=offset,
                                       offset_type=offset_type,
                                       type=type,
                                       sent=sent,
                                       from_admin=from_admin,
                                       event=event,
                                       homework=homework,
                                       user=user)

    return reminder


def verify_reminder_matches_data(test_case, reminder, data):
    test_case.assertEqual(reminder.title, data['title'])
    test_case.assertEqual(reminder.message, data['message'])
    test_case.assertEqual(reminder.start_of_range, parser.parse(data['start_of_range']))
    test_case.assertEqual(reminder.offset, data['offset'])
    test_case.assertEqual(reminder.offset_type, data['offset_type'])
    test_case.assertEqual(reminder.type, data['type'])
    test_case.assertEqual(reminder.sent, data['sent'])
    test_case.assertEqual(reminder.from_admin, data['from_admin'])
    if 'event' in data and data['event']:
        test_case.assertEqual(reminder.event.pk, data['event'])
    if 'homework' in data and data['homework']:
        test_case.assertEqual(reminder.homework.pk, data['homework'])
    test_case.assertEqual(reminder.user.pk, data['user'])
