import datetime
import json
import logging
from urllib.request import urlopen, URLError

import icalendar
import pytz
from dateutil import parser
from django.conf import settings
from django.core import validators
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status

from helium.common import enums
from helium.common.utils.commonutils import HeliumError
from helium.planner.models import Event
from helium.planner.serializers.eventserializer import EventSerializer

__author__ = "Alex Laird"
__copyright__ = "Copyright 2019, Helium Edu"
__version__ = "1.4.37"

logger = logging.getLogger(__name__)

url_validator = validators.URLValidator()


class HeliumICalError(HeliumError):
    pass


def _get_cache_prefix(external_calendar):
    return "users:{}:externalcalendars:{}:events".format(external_calendar.get_user().pk, external_calendar.pk)


def _get_events_from_cache(external_calendar, cached_value):
    events = []
    invalid_data = False

    try:
        for event in json.loads(cached_value):
            event = Event(id=event['id'],
                          title=event['title'],
                          all_day=event['all_day'],
                          show_end_time=event['show_end_time'],
                          start=parser.parse(event['start']),
                          end=parser.parse(event['end']),
                          owner_id=event['owner_id'],
                          user_id=event['user'],
                          calendar_item_type=event['calendar_item_type'],
                          url=event['url'],
                          comments=event['comments'])
            events.append(event)
    except:
        invalid_data = True

    if invalid_data:
        events = []
        cache.delete(_get_cache_prefix(external_calendar))

    return events, not invalid_data


def _create_events_from_calendar(external_calendar, calendar):
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

    serializer = EventSerializer(events, many=True)
    events_json = json.dumps(serializer.data)
    if len(events_json.encode('utf-8')) <= settings.FEED_MAX_CACHEABLE_SIZE:
        cache.set(_get_cache_prefix(external_calendar), events_json, settings.FEED_CACHE_TTL)

    return events


def validate_url(url):
    """
    Validates that a given URL maps to a valid ICAL feed. Validation includes both simple HTTP validation as well as
    downloading and parsing the calendar itself to ensure it is valid. As such, since we parse the full calendar to
    ensure its validity, a Calendar object is also returned if validation is successful.

    :param url: The ICAL URL to validate
    :return: The validated ICAL feed in a Calendar object
    """
    try:
        url_validator(url)

        response = urlopen(url)

        if response.getcode() != status.HTTP_200_OK:
            raise HeliumICalError("The URL did not return a valid response.")

        return icalendar.Calendar.from_ical(response.read())
    except ValidationError as ex:
        logger.info("The URL is invalid: {}".format(ex))

        raise HeliumICalError(ex.message)
    except URLError as ex:
        logger.info("The URL is not reachable: {}".format(ex))

        raise HeliumICalError("The URL is not reachable.")
    except ValueError as ex:
        logger.info("The URL did not return a valid ICAL feed: {}".format(ex))

        raise HeliumICalError("The URL did not return a valid ICAL feed.")


def calendar_to_events(external_calendar):
    """
    For the given external calendar model and parsed ICAL calendar, convert each item in the calendar to an event
    resources.

    :param external_calendar: The external calendar source that is referenced by the calendar object.
    :return: A list of event resources.
    """
    events = []

    cached = False
    cached_value = cache.get(_get_cache_prefix(external_calendar))
    if cached_value:
        events, cached = _get_events_from_cache(external_calendar, cached_value)

    if not cached:
        calendar = validate_url(external_calendar.url)

        events = _create_events_from_calendar(external_calendar, calendar)

    return events
