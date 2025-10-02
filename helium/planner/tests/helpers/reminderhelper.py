__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.7"

from dateutil import parser

from helium.common import enums
from helium.planner.models import Reminder


def given_reminder_exists(user, title='🌴 Test Reminder', message='You need to do something now.', offset=15,
                          offset_type=enums.MINUTES, type=enums.TEXT, sent=False, event=None, homework=None):
    reminder = Reminder.objects.create(title=title,
                                       message=message,
                                       offset=offset,
                                       offset_type=offset_type,
                                       type=type,
                                       sent=sent,
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
    if 'event' in data and data['event']:
        if isinstance(data['event'], dict):
            test_case.assertEqual(reminder.event.pk, int(data['event']['id']))
        else:
            test_case.assertEqual(reminder.event.pk, int(data['event']))
    if 'homework' in data and data['homework']:
        if isinstance(data['homework'], dict):
            test_case.assertEqual(reminder.homework.pk, int(data['homework']['id']))
        else:
            test_case.assertEqual(reminder.homework.pk, int(data['homework']))
    if isinstance(data['user'], dict):
        test_case.assertEqual(reminder.user.pk, int(data['user']['id']))
    else:
        test_case.assertEqual(reminder.user.pk, int(data['user']))
