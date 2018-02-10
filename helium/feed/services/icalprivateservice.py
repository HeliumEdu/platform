import datetime
import logging

import icalendar
import pytz
from django.conf import settings
from django.utils import timezone

from helium.planner.models import Homework, Course
from helium.planner.services import coursescheduleservice

__author__ = "Alex Laird"
__copyright__ = "Copyright 2018, Helium Edu"
__version__ = '1.3.1'

logger = logging.getLogger(__name__)


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
    description = "Comments: {}".format(event.comments)

    if event.url:
        description = "URL: {}\n".format(event.url) + description

    return description


def __create_homework_description(homework):
    class_info = homework.course.title
    if homework.category and homework.category.title != "Uncategorized":
        class_info = "{} for {}".format(homework.category.title, class_info)
    if homework.course.room:
        class_info += " in {}".format(homework.course.room)

    materials = []
    for material in homework.materials.iterator():
        materials.append(material.title)

    description = "Class Info: {}\n".format(class_info)

    if len(materials) > 0:
        description += "Materials: {}\n".format(",".join(materials))

    if homework.url:
        description += "URL: {}\n".format(homework.url)

    if homework.completed and homework.current_grade != "-1/100":
        description += "Grade: {}\n".format(homework.current_grade)

    description += "Comments: {}".format(homework.comments)

    return description


def events_to_private_ical_feed(user):
    """
    Generate an ICAL feed for all events associated with the given user.

    :param user: The user to generate an ICAL feed for.
    :return: An ICAL string of all the user's events.
    """
    # TODO: responses should, in the future, be cached for at least a few minutes

    timezone.activate(pytz.timezone(user.settings.time_zone))

    calendar = __create_calendar(user)

    for event in user.events.iterator():
        calendar_event = icalendar.Event()
        calendar_event["uid"] = "he-{}-{}".format(user.pk, event.pk)
        calendar_event["summary"] = event.title
        calendar_event["dtstamp"] = icalendar.vDatetime(timezone.localtime(event.created_at))
        if not event.all_day:
            calendar_event["dtstart"] = icalendar.vDatetime(timezone.localtime(event.start))
            calendar_event["dtend"] = icalendar.vDatetime(timezone.localtime(event.end))
        else:
            calendar_event["dtstart"] = icalendar.vDate(event.start)
            calendar_event["dtend"] = icalendar.vDate((event.end + datetime.timedelta(days=1)))
        calendar_event["description"] = __create_event_description(event)

        calendar.add_component(calendar_event)

    timezone.deactivate()

    return calendar.to_ical()


def homework_to_private_ical_feed(user):
    """
    Generate an ICAL feed for all homework associated with the given user.

    :param user: The user to generate an ICAL feed for.
    :return: An ICAL string of all the user's homework.
    """
    # TODO: responses should, in the future, be cached for at least a few minutes

    timezone.activate(pytz.timezone(user.settings.time_zone))

    calendar = __create_calendar(user)

    for homework in Homework.objects.for_user(user.pk).iterator():
        calendar_event = icalendar.Event()
        calendar_event["uid"] = "he-{}-{}".format(user.pk, homework.pk)
        calendar_event["summary"] = homework.title
        calendar_event["dtstamp"] = icalendar.vDatetime(timezone.localtime(homework.created_at))
        if not homework.all_day:
            calendar_event["dtstart"] = icalendar.vDatetime(timezone.localtime(homework.start))
            calendar_event["dtend"] = icalendar.vDatetime(timezone.localtime(homework.end))
        else:
            calendar_event["dtstart"] = icalendar.vDate(homework.start)
            calendar_event["dtend"] = icalendar.vDate((homework.end + datetime.timedelta(days=1)))
        calendar_event["description"] = __create_homework_description(homework)

        calendar.add_component(calendar_event)

    timezone.deactivate()

    return calendar.to_ical()


def courseschedules_to_private_ical_feed(user):
    """
    Generate an ICAL feed for all course schedules associated with the given user.

    :param user: The user to generate an ICAL feed for.
    :return: An ICAL string of all the user's course schedules.
    """
    # TODO: responses should, in the future, be cached for at least a few minutes

    calendar = __create_calendar(user)

    events = []
    for course in Course.objects.for_user(user.pk):
        events += coursescheduleservice.course_schedules_to_events(course, course.schedules)

    timezone.activate(pytz.timezone(user.settings.time_zone))

    for event in events:
        calendar_event = icalendar.Event()
        calendar_event["uid"] = "he-{}-{}".format(user.pk, event.pk)
        calendar_event["summary"] = event.title
        calendar_event["dtstamp"] = icalendar.vDatetime(timezone.localtime(event.created_at))
        if not event.all_day:
            calendar_event["dtstart"] = icalendar.vDatetime(timezone.localtime(event.start))
            calendar_event["dtend"] = icalendar.vDatetime(timezone.localtime(event.end))
        else:
            calendar_event["dtstart"] = icalendar.vDate(event.start)
            calendar_event["dtend"] = icalendar.vDate((event.end + datetime.timedelta(days=1)))
        calendar_event["description"] = __create_event_description(event)

        calendar.add_component(calendar_event)

    timezone.deactivate()

    return calendar.to_ical()
