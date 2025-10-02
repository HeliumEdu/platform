__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.10.7"

from helium.feed.models import ExternalCalendar


def given_external_calendar_exists(user, title='📅 My Calendar', url='http://go.com/valid-ical-feed', color='#fad165',
                                   shown_on_calendar=True):
    external_calendar = ExternalCalendar.objects.create(title=title,
                                                        url=url,
                                                        color=color,
                                                        shown_on_calendar=shown_on_calendar,
                                                        user=user)

    return external_calendar


def verify_externalcalendar_matches_data(test_case, external_calendar, data):
    test_case.assertEqual(external_calendar.title, data['title'])
    test_case.assertEqual(external_calendar.url, data['url'])
    test_case.assertEqual(external_calendar.color, data['color'])
    test_case.assertEqual(external_calendar.shown_on_calendar, data['shown_on_calendar'])
    test_case.assertEqual(external_calendar.user.pk, data['user'])
