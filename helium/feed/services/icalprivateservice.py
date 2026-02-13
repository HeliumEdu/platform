__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import datetime
import logging

import icalendar
import pytz
from django.conf import settings
from django.db.models import Max
from django.http import HttpResponse
from django.utils import timezone
from django.utils.http import http_date, parse_http_date_safe

from helium.planner.models import Homework, Course, CourseSchedule, CourseGroup, Category

from helium.planner.services import coursescheduleservice

logger = logging.getLogger(__name__)


def get_events_last_modified(user) -> datetime.datetime | None:
    """
    Get the maximum updated_at timestamp from all events for a user.

    :param user: The user whose events to check.
    :return: The max updated_at datetime, or None if no events exist.
    """
    return user.events.aggregate(Max('updated_at'))['updated_at__max']


def get_homework_last_modified(user) -> datetime.datetime | None:
    """
    Get the maximum updated_at timestamp from homework, courses, and categories for a user.

    :param user: The user whose homework-related models to check.
    :return: The max updated_at datetime across all related models, or None if no data exists.
    """
    homework_max = Homework.objects.for_user(user.pk).aggregate(Max('updated_at'))['updated_at__max']
    course_max = Course.objects.for_user(user.pk).aggregate(Max('updated_at'))['updated_at__max']
    category_max = Category.objects.for_user(user.pk).aggregate(Max('updated_at'))['updated_at__max']

    timestamps = [t for t in [homework_max, course_max, category_max] if t is not None]
    return max(timestamps) if timestamps else None


def get_courseschedules_last_modified(user) -> datetime.datetime | None:
    """
    Get the maximum updated_at timestamp from course schedules, courses, and course groups for a user.

    :param user: The user whose course schedule-related models to check.
    :return: The max updated_at datetime across all related models, or None if no data exists.
    """
    schedule_max = CourseSchedule.objects.for_user(user.pk).aggregate(Max('updated_at'))['updated_at__max']
    course_max = Course.objects.for_user(user.pk).aggregate(Max('updated_at'))['updated_at__max']
    course_group_max = CourseGroup.objects.for_user(user.pk).aggregate(Max('updated_at'))['updated_at__max']

    timestamps = [t for t in [schedule_max, course_max, course_group_max] if t is not None]
    return max(timestamps) if timestamps else None


def generate_etag(user_id: int, last_modified: datetime.datetime | None) -> str:
    """
    Generate an ETag from user ID and timestamp.

    :param user_id: The user's primary key.
    :param last_modified: The last modified datetime, or None for empty feeds.
    :return: An ETag string in the format '"{user_id}:{timestamp}"' or '"{user_id}:0"' if no timestamp.
    """
    if last_modified is None:
        return f'"{user_id}:0"'
    timestamp = int(last_modified.timestamp())
    return f'"{user_id}:{timestamp}"'


def check_conditional_request(request, etag: str, last_modified: datetime.datetime | None) -> HttpResponse | None:
    """
    Check if the request contains conditional headers that match the current state.

    :param request: The HTTP request object.
    :param etag: The current ETag for the resource.
    :param last_modified: The last modified datetime for the resource.
    :return: A 304 Not Modified response if conditions match, else None.
    """
    # Check If-None-Match header
    if_none_match = request.META.get('HTTP_IF_NONE_MATCH')
    if if_none_match:
        # ETags can be comma-separated
        etags = [e.strip() for e in if_none_match.split(',')]
        if etag in etags or '*' in etags:
            response = HttpResponse(status=304)
            response['ETag'] = etag
            return response

    # Check If-Modified-Since header
    if_modified_since = request.META.get('HTTP_IF_MODIFIED_SINCE')
    if if_modified_since and last_modified:
        parsed_time = parse_http_date_safe(if_modified_since)
        if parsed_time is not None:
            # HTTP dates have 1-second precision, so use >= comparison
            if int(last_modified.timestamp()) <= parsed_time:
                response = HttpResponse(status=304)
                response['ETag'] = etag
                return response

    return None


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

        for homework in Homework.objects.for_user(user.pk).select_related('category', 'course').prefetch_related('materials'):
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
    for course in Course.objects.for_user(user.pk).select_related('course_group', 'course_group__user', 'course_group__user__settings'):
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
