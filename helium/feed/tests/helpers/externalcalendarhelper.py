"""
Helper for ExternalCalendar models in testing.
"""

from helium.feed.models import ExternalCalendar

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'


def given_external_calendar_exists(user, title='', url='http://test.com', color='#4442', shown_on_calendar=True):
    external_calendar = ExternalCalendar.objects.create(title=title,
                                                        url=url,
                                                        color=color,
                                                        shown_on_calendar=shown_on_calendar,
                                                        user=user)

    return external_calendar
