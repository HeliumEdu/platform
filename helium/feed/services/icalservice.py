import datetime
import logging
from urllib.request import urlopen, URLError

import icalendar
import pytz
from django.conf import settings
from django.utils import timezone
from icalendar import Calendar
from rest_framework import status

from helium.common import enums
from helium.common.utils.commonutils import HeliumError
from helium.planner.models import Event, Homework

__author__ = "Alex Laird"
__copyright__ = "Copyright 2018, Helium Edu"
__version__ = '1.2.0'

logger = logging.getLogger(__name__)


class ICalError(HeliumError):
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
            raise ICalError("The URL did not return a valid response.")

        # TODO: responses should, in the future, be cached for at least a few minutes
        return Calendar.from_ical(response.read())
    except URLError as ex:
        logger.info("The URL is not reachable: {}".format(ex))

        raise ICalError("The URL is not reachable.")
    except ValueError as ex:
        logger.info("The URL did not return a valid ICAL feed: {}".format(ex))

        raise ICalError("The URL did not return a valid ICAL feed.")


def calendar_to_external_events(external_calendar, calendar):
    """
    For the given external calendar model and parsed ICAL calendar, convert each item in the calendar to an external
    event resources.

    :param external_calendar: The external calendar source that is referenced by the calendar object.
    :param calendar: The calendar object that is being parsed.
    :return: A list of external event resources.
    """
    external_events = []

    time_zone = pytz.timezone(external_calendar.get_user().settings.time_zone)
    for component in calendar.walk():
        if component.name == "VTIMEZONE":
            time_zone = pytz.timezone(component.get("TZID"))
        elif component.name == "VEVENT":
            start = component.get("dtstart").dt
            end = component.get("dtend").dt
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

            event = Event(title=component.get("summary"),
                          all_day=all_day,
                          show_end_time=show_end_time,
                          start=start,
                          end=end,
                          url=component.get("url"),
                          comments=component.get("description"),
                          user=external_calendar.get_user(),
                          calendar_item_type=enums.EXTERNAL)

            external_events.append(event)

    return external_events


def __create_calendar(user):
    calendar = icalendar.Calendar()

    calendar.add("PRODID", "-//Helium Edu//{}//EN".format(settings.PROJECT_VERSION))
    calendar.add("VERSION", "2.0")
    calendar.add("CALSCALE", "GREGORIAN")
    calendar.add("METHOD", "PUBLISH")
    calendar.add("X-WR-CALNAME", "{} for {}".format(settings.PROJECT_NAME, user.username))
    calendar.add("X-WR-CALDESC", "{} for {}".format(settings.PROJECT_NAME, user.username))

    return calendar


def __create_event_description(event):
    description = event.comments

    if event.url:
        description = "URL: {}\n".format(event.url) + description

    return description


def __create_homework_description(homework):
    class_info = homework.course.title
    if homework.category and homework.category.title != "Uncategorized":
        "{} for {}".format(homework.category.title, class_info)
    if homework.course.room:
        "{} in {}".format(class_info, homework.course.room)

    materials = []
    for material in homework.materials.iterator():
        materials.append(material.title)

    description = "Class Info: {}\n".format(class_info)

    if len(materials) > 0:
        description += "Materials: {}\n".format(",".join(materials))

    if homework.url:
        description = "URL: {}\n".format(homework.url)

    if homework.completed and homework.current_grade != "-1/100":
        description = "Grade: {}\n".format(homework.current_grade)

    description += homework.comments

    return description


def events_to_private_ical_feed(user):
    timezone.activate(pytz.timezone(user.settings.time_zone))

    calendar = __create_calendar(user)

    for event in user.events.iterator():
        calendar_event = icalendar.Event()
        calendar_event["uid"] = "he-{}-{}".format(user.pk, event.pk)
        calendar_event["summary"] = event.title
        calendar_event["dtstamp"] = icalendar.vDatetime(event.created_at)
        if not event.all_day:
            calendar_event["dtstart"] = icalendar.vDatetime(event.start)
            calendar_event["dtend"] = icalendar.vDatetime(event.end)
        else:
            calendar_event["dtstart"] = icalendar.vDate(event.start)
            calendar_event["dtend"] = icalendar.vDate((event.end + datetime.timedelta(days=1)))
        calendar_event["description"] = __create_event_description(event)

        calendar.add_component(calendar_event)

    timezone.deactivate()

    return calendar.to_ical()


def homework_to_private_ical_feed(user):
    timezone.activate(pytz.timezone(user.settings.time_zone))

    calendar = __create_calendar(user)

    for homework in Homework.objects.for_user(user.pk).iterator():
        calendar_event = icalendar.Event()
        calendar_event["uid"] = "he-{}-{}".format(user.pk, homework.pk)
        calendar_event["summary"] = homework.title
        calendar_event["dtstamp"] = icalendar.vDatetime(homework.created_at)
        if not homework.all_day:
            calendar_event["dtstart"] = icalendar.vDatetime(homework.start)
            calendar_event["dtend"] = icalendar.vDatetime(homework.end)
        else:
            calendar_event["dtstart"] = icalendar.vDate(homework.start)
            calendar_event["dtend"] = icalendar.vDate((homework.end + datetime.timedelta(days=1)))
        calendar_event["description"] = __create_homework_description(homework)

        calendar.add_component(calendar_event)

    timezone.deactivate()

    return calendar.to_ical()
