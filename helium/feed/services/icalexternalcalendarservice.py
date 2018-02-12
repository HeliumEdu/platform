import datetime
import logging
from urllib.request import urlopen, URLError

import icalendar
import pytz
from django.utils import timezone
from rest_framework import status

from helium.common import enums
from helium.common.utils.commonutils import HeliumError
from helium.planner.models import Event

__author__ = "Alex Laird"
__copyright__ = "Copyright 2018, Helium Edu"
__version__ = '1.3.3'

logger = logging.getLogger(__name__)


class HeliumICalError(HeliumError):
    pass


def validate_url(url):
    """
    Validates that a given URL maps to a valid ICAL feed. Validation includes both simple HTTP validation as well as
    downloading and parsing the calendar itself to ensure it is valid. As such, since we parse the full calendar to
    ensure its validity, a Calendar object is also returned if validation is successful.

    :param url: The ICAL URL to validate
    :return: The validated ICAL feed in a Calendar object
    """
    try:
        response = urlopen(url)

        if response.getcode() != status.HTTP_200_OK:
            raise HeliumICalError("The URL did not return a valid response.")

        # TODO: responses should, in the future, be cached for at least a few minutes
        return icalendar.Calendar.from_ical(response.read())
    except URLError as ex:
        logger.info("The URL is not reachable: {}".format(ex))

        raise HeliumICalError("The URL is not reachable.")
    except ValueError as ex:
        logger.info("The URL did not return a valid ICAL feed: {}".format(ex))

        raise HeliumICalError("The URL did not return a valid ICAL feed.")


def calendar_to_events(external_calendar, calendar):
    """
    For the given external calendar model and parsed ICAL calendar, convert each item in the calendar to an event
    resources.

    :param external_calendar: The external calendar source that is referenced by the calendar object.
    :param calendar: The calendar object that is being parsed.
    :return: A list of event resources.
    """
    events = []

    time_zone = pytz.timezone(external_calendar.get_user().settings.time_zone)
    for component in calendar.walk():
        if component.name == "VTIMEZONE":
            time_zone = pytz.timezone(component.get("TZID"))
        elif component.name == "VEVENT":
            start = component.get("DTSTART").dt
            end = component.get("DTEND").dt
            all_day = not isinstance(start, datetime.datetime)
            show_end_time = isinstance(start, datetime.datetime)

            if all_day:
                start = datetime.datetime.combine(start, datetime.time.min)
            if timezone.is_naive(start):
                start = timezone.make_aware(start, time_zone)
            start = start.astimezone(pytz.utc)

            if all_day:
                end = datetime.datetime.combine(end, datetime.time.min)
            if timezone.is_naive(end):
                end = timezone.make_aware(end, time_zone)
            end = end.astimezone(pytz.utc)

            event = Event(id=len(events),
                          title=component.get("SUMMARY"),
                          all_day=all_day,
                          show_end_time=show_end_time,
                          start=start,
                          end=end,
                          url=component.get("URL"),
                          comments=component.get("DESCRIPTION"),
                          user=external_calendar.get_user(),
                          calendar_item_type=enums.EXTERNAL)

            events.append(event)

    return events
