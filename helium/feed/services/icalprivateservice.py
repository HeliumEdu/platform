__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.52"

import datetime
import logging

import icalendar
import pytz
from django.conf import settings
from django.utils import timezone

from helium.planner.models import Homework, Course
from helium.planner.services import coursescheduleservice

logger = logging.getLogger(__name__)


def _create_calendar(user):
    calendar = icalendar.Calendar()

    calendar.add("PRODID", f"-//Helium Edu//{settings.PROJECT_VERSION}//EN")
    calendar.add("VERSION", "2.0")
    calendar.add("CALSCALE", "GREGORIAN")
    calendar.add("METHOD", "PUBLISH")
    calendar.add("X-WR-CALNAME", f"{settings.PROJECT_NAME} for {user.username}")
    calendar.add("X-WR-CALDESC", f"{settings.PROJECT_NAME} for {user.username}")

    return calendar


def _create_event_description(event):
    description = f"Comments: {event.comments}"

    if event.url:
        description = f"URL: {event.url}\n" + description

    return description


def _create_homework_description(homework):
    class_info = homework.course.title
    if homework.category and homework.category.title != "Uncategorized":
        class_info = f"{homework.category.title} for {class_info}"
    if homework.course.room:
        class_info += f" in {homework.course.room}"

    materials = []
    for material in homework.materials.iterator():
        materials.append(material.title)

    description = f"Class Info: {class_info}\n"

    if len(materials) > 0:
        description += f"Materials: {','.join(materials)}\n"

    if homework.url:
        description += f"URL: {homework.url}\n"

    if homework.completed and homework.current_grade != "-1/100":
        description += f"Grade: {homework.current_grade}\n"

    description += f"Comments: {homework.comments}"

    return description


def events_to_private_ical_feed(user):
    """
    Generate an ICAL feed for all events associated with the given user.

    :param user: The user to generate an ICAL feed for.
    :return: An ICAL string of all the user's events.
    """
    timezone.activate(pytz.timezone(user.settings.time_zone))

    try:
        calendar = _create_calendar(user)

        for event in user.events.iterator():
            calendar_event = icalendar.Event()
            calendar_event["UID"] = f"he-{user.pk}-{event.pk}"
            calendar_event["SUMMARY"] = event.title
            calendar_event["DTSTAMP"] = icalendar.vDatetime(timezone.localtime(event.created_at))
            if not event.all_day:
                calendar_event["DTSTART"] = icalendar.vDatetime(timezone.localtime(event.start))
                calendar_event["DTEND"] = icalendar.vDatetime(timezone.localtime(event.end))
            else:
                calendar_event["DTSTART"] = icalendar.vDate(event.start)
                calendar_event["DTEND"] = icalendar.vDate((event.end + datetime.timedelta(days=1)))
            calendar_event["DESCRIPTION"] = _create_event_description(event)

            calendar.add_component(calendar_event)
    except:
        logger.error("An unknown error occurred.", exc_info=True)
    timezone.deactivate()

    return calendar.to_ical()


def homework_to_private_ical_feed(user):
    """
    Generate an ICAL feed for all homework associated with the given user.

    :param user: The user to generate an ICAL feed for.
    :return: An ICAL string of all the user's homework.
    """
    timezone.activate(pytz.timezone(user.settings.time_zone))

    try:
        calendar = _create_calendar(user)

        for homework in Homework.objects.for_user(user.pk).iterator():
            calendar_event = icalendar.Event()
            calendar_event["UID"] = f"he-{user.pk}-{homework.pk}"
            calendar_event["SUMMARY"] = homework.title
            calendar_event["DTSTAMP"] = icalendar.vDatetime(timezone.localtime(homework.created_at))
            if not homework.all_day:
                calendar_event["DTSTART"] = icalendar.vDatetime(timezone.localtime(homework.start))
                calendar_event["DTEND"] = icalendar.vDatetime(timezone.localtime(homework.end))
            else:
                calendar_event["DTSTART"] = icalendar.vDate(homework.start)
                calendar_event["DTEND"] = icalendar.vDate((homework.end + datetime.timedelta(days=1)))
            calendar_event["DESCRIPTION"] = _create_homework_description(homework)

            calendar.add_component(calendar_event)
    except:
        logger.error("An unknown error occurred.", exc_info=True)

    timezone.deactivate()

    return calendar.to_ical()


def courseschedules_to_private_ical_feed(user):
    """
    Generate an ICAL feed for all course schedules associated with the given user.

    The IDs given for each event are sequential, unique only amongst the results of this particular query, and not
    guaranteed to be consistent across calls.

    :param user: The user to generate an ICAL feed for.
    :return: An ICAL string of all the user's course schedules.
    """
    calendar = _create_calendar(user)

    events = []
    for course in Course.objects.for_user(user.pk).iterator():
        events += coursescheduleservice.course_schedules_to_events(course, course.schedules)

    timezone.activate(pytz.timezone(user.settings.time_zone))

    try:
        for event in events:
            calendar_event = icalendar.Event()
            calendar_event["UID"] = f"he-{user.pk}-{event.pk}"
            calendar_event["SUMMARY"] = event.title
            calendar_event["DTSTAMP"] = icalendar.vDatetime(timezone.localtime(event.created_at))
            if not event.all_day:
                calendar_event["DTSTART"] = icalendar.vDatetime(timezone.localtime(event.start))
                calendar_event["DTEND"] = icalendar.vDatetime(timezone.localtime(event.end))
            else:
                calendar_event["DTSTART"] = icalendar.vDate(event.start)
                calendar_event["DTEND"] = icalendar.vDate((event.end + datetime.timedelta(days=1)))
            calendar_event["DESCRIPTION"] = _create_event_description(event)

            calendar.add_component(calendar_event)
    except:
        logger.error("An unknown error occurred.", exc_info=True)

    timezone.deactivate()

    return calendar.to_ical()
