import datetime
from zoneinfo import ZoneInfo

from dateutil import parser

from helium.planner.models import Event


def given_event_exists(user, title='🏀 Test Event', all_day=False, show_end_time=True,
                       start=datetime.datetime(2017, 5, 8, 12, 0, 0, tzinfo=datetime.timezone.utc),
                       end=datetime.datetime(2017, 5, 8, 14, 0, 0, tzinfo=datetime.timezone.utc),
                       priority=75, url='', owner_id='12345',
                       recurrence_rule=None, exception_dates=None):
    event = Event.objects.create(title=title,
                                 all_day=all_day,
                                 show_end_time=show_end_time,
                                 start=start,
                                 end=end,
                                 priority=priority,
                                 url=url,
                                 owner_id=owner_id,
                                 recurrence_rule=recurrence_rule,
                                 exception_dates=exception_dates,
                                 user=user)

    return event


def given_weekly_event_exists(user, start=None, recurrence_rule='FREQ=WEEKLY;BYDAY=MO', **kwargs):
    start = start or datetime.datetime(2030, 4, 1, 9, 0, tzinfo=ZoneInfo(user.settings.time_zone))
    return given_event_exists(user, start=start, end=start + datetime.timedelta(hours=1),
                              recurrence_rule=recurrence_rule, **kwargs)


def verify_event_matches_data(test_case, event, data):
    test_case.assertEqual(event.title, data['title'])
    test_case.assertEqual(event.all_day, data['all_day'])
    test_case.assertEqual(event.show_end_time, data['show_end_time'])
    test_case.assertEqual(event.start, parser.parse(data['start']))
    test_case.assertEqual(event.end, parser.parse(data['end']))
    test_case.assertEqual(event.priority, data['priority'])
    if 'url' in data:
        test_case.assertEqual(event.url, data['url'])
    test_case.assertEqual(event.owner_id, data['owner_id'])
    if 'recurrence_rule' in data:
        test_case.assertEqual(event.recurrence_rule, data['recurrence_rule'])
    if 'exception_dates' in data:
        expected = data['exception_dates']
        actual = event.exception_dates
        if expected is None or actual is None:
            test_case.assertEqual(actual, expected)
        else:
            test_case.assertEqual(
                [parser.parse(d) for d in actual],
                [parser.parse(d) for d in expected],
            )
    if 'calendar_item_type' in data:
        test_case.assertEqual(event.calendar_item_type, data['calendar_item_type'])
    test_case.assertEqual(event.user.pk, int(data['user']))
