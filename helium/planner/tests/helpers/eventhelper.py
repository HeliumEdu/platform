__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.54"

import datetime

from dateutil import parser
from django.utils import timezone

from helium.planner.models import Event


def given_event_exists(user, title='🏀 Test Event', all_day=False, show_end_time=True,
                       start=datetime.datetime(2017, 5, 8, 12, 0, 0, tzinfo=timezone.utc),
                       end=datetime.datetime(2017, 5, 8, 14, 0, 0, tzinfo=timezone.utc),
                       priority=75, comments='A comment on an event.', owner_id='12345'):
    event = Event.objects.create(title=title,
                                 all_day=all_day,
                                 show_end_time=show_end_time,
                                 start=start,
                                 end=end,
                                 priority=priority,
                                 comments=comments,
                                 owner_id=owner_id,
                                 user=user)

    return event


def verify_event_matches_data(test_case, event, data):
    test_case.assertEqual(event.title, data['title'])
    test_case.assertEqual(event.all_day, data['all_day'])
    test_case.assertEqual(event.show_end_time, data['show_end_time'])
    test_case.assertEqual(event.start, parser.parse(data['start']))
    test_case.assertEqual(event.end, parser.parse(data['end']))
    test_case.assertEqual(event.priority, data['priority'])
    test_case.assertEqual(event.comments, data['comments'])
    test_case.assertEqual(event.owner_id, data['owner_id'])
    test_case.assertEqual(event.user.pk, int(data['user']))
