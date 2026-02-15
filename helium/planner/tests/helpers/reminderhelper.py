__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

from dateutil import parser

from helium.common import enums
from helium.planner.models import Reminder


def given_reminder_exists(user, title='🌴 Test Reminder', message='You need to do something now.', offset=15,
                          offset_type=enums.MINUTES, type=enums.TEXT, sent=False, dismissed=False, repeating=False,
                          event=None, homework=None, course=None):
    reminder = Reminder.objects.create(title=title,
                                       message=message,
                                       offset=offset,
                                       offset_type=offset_type,
                                       type=type,
                                       sent=sent,
                                       dismissed=dismissed,
                                       repeating=repeating,
                                       event=event,
                                       homework=homework,
                                       course=course,
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
    test_case.assertEqual(reminder.dismissed, data['dismissed'])
    test_case.assertEqual(reminder.repeating, data.get('repeating', False))
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
    if 'course' in data and data['course']:
        if isinstance(data['course'], dict):
            test_case.assertEqual(reminder.course.pk, int(data['course']['id']))
        else:
            test_case.assertEqual(reminder.course.pk, int(data['course']))
    if isinstance(data['user'], dict):
        test_case.assertEqual(reminder.user.pk, int(data['user']['id']))
    else:
        test_case.assertEqual(reminder.user.pk, int(data['user']))
