import datetime
import logging
from zoneinfo import ZoneInfo

import icalendar
from django.conf import settings
from django.db.models import Max
from django.http import HttpResponse
from django.utils import timezone
from django.utils.http import parse_http_date_safe

from helium.planner.models import Homework, Course, CourseSchedule, CourseGroup, Category

from helium.planner.services import coursescheduleservice
from helium.planner.utils import noteutils

logger = logging.getLogger(__name__)


def get_events_last_modified(user) -> datetime.datetime | None:
    """
    Get the maximum updated_at timestamp from all events for a user, also
    accounting for any deletions via the user's last_deletion_at timestamp.

    :param user: The user whose events to check.
    :return: The max updated_at datetime, or None if no events exist and no deletions have occurred.
    """
    event_max = user.events.aggregate(Max('updated_at'))['updated_at__max']
    timestamps = [t for t in [event_max, user.settings.last_deletion_at] if t is not None]
    return max(timestamps) if timestamps else None


def get_homework_last_modified(user) -> datetime.datetime | None:
    """
    Get the maximum updated_at timestamp from homework, courses, categories, and course groups for a user.

    :param user: The user whose homework-related models to check.
    :return: The max updated_at datetime across all related models, or None if no data exists.
    """
    homework_max = Homework.objects.for_user(user.pk).aggregate(Max('updated_at'))['updated_at__max']
    course_max = Course.objects.for_user(user.pk).aggregate(Max('updated_at'))['updated_at__max']
    category_max = Category.objects.for_user(user.pk).aggregate(Max('updated_at'))['updated_at__max']
    # Hiding a course group removes its homework from the feed
    course_group_max = CourseGroup.objects.for_user(user.pk).aggregate(Max('updated_at'))['updated_at__max']

    timestamps = [t for t in [homework_max, course_max, category_max, course_group_max,
                              user.settings.last_deletion_at] if t is not None]
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

    timestamps = [t for t in [schedule_max, course_max, course_group_max, user.settings.last_deletion_at] if t is not None]
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


def _create_calendar(name):
    """
    Start a feed's calendar. Its name says what the feed holds, never who it belongs to: a feed URL can reach
    anyone, so nothing in it identifies the user (``UID`` values use the user's pk).

    :param name: The calendar's name, e.g. "Helium Assignments".
    """
    calendar = icalendar.Calendar()

    calendar.add("PRODID", f"-//Helium Edu, LLC//{settings.PROJECT_VERSION}//EN")
    calendar.add("VERSION", "2.0")
    calendar.add("CALSCALE", "GREGORIAN")
    calendar.add("METHOD", "PUBLISH")
    calendar.add("X-WR-CALNAME", name)
    calendar.add("X-WR-CALDESC", name)

    return calendar


def _note_line(notes_set):
    url = noteutils.note_url(notes_set)
    return f"\U0001F517 Note: {url}" if url else ""


def _create_event_description(event):
    lines = [
        f"URL: {event.url}" if event.url else "",
        _note_line(event.notes_set),
    ]

    return "\n".join(line for line in lines if line)


def _create_homework_description(homework):
    class_info = homework.course.title
    if homework.category and homework.category.title != "Uncategorized":
        class_info = f"{homework.category.title} for {class_info}"
    if homework.course.room:
        class_info += f" in {homework.course.room}"

    resources = []
    for resource in homework.resources.all():
        resources.append(resource.title)

    description = f"Class Info: {class_info}\n"

    if len(resources) > 0:
        description += f"Resources: {','.join(resources)}\n"

    if homework.url:
        description += f"URL: {homework.url}\n"

    if homework.completed:
        description += "Status: Complete\n"
        if homework.current_grade != "-1/100":
            description += f"Grade: {homework.current_grade}\n"

    description += _note_line(homework.notes_set)

    return description.rstrip("\n")


def _create_course_schedule_description(course):
    """
    Describe a class meeting in plain text, as an ICS description must be: the app's comments link the title as HTML,
    which calendar apps would show as literal tags.
    """
    description = f"Comments: {coursescheduleservice.get_comments(course, link=False)}"
    if course.website:
        description = f"URL: {course.website}\n" + description

    return description


def _to_vevent(user, item):
    calendar_event = icalendar.Event()
    calendar_event["UID"] = f"he-{user.pk}-{item.pk}"
    calendar_event["SUMMARY"] = item.title
    calendar_event["DTSTAMP"] = icalendar.vDatetime(timezone.localtime(item.created_at))
    if not item.all_day:
        calendar_event["DTSTART"] = icalendar.vDatetime(timezone.localtime(item.start))
        calendar_event["DTEND"] = icalendar.vDatetime(timezone.localtime(item.end))
    else:
        calendar_event["DTSTART"] = icalendar.vDate(timezone.localtime(item.start).date())
        calendar_event["DTEND"] = icalendar.vDate(timezone.localtime(item.end).date())
    return calendar_event


def _add_recurrence(calendar_event, item):
    calendar_event.add('RRULE', icalendar.vRecur.from_ical(item.recurrence_rule))
    if item.exception_dates:
        exception_dates = [timezone.localtime(datetime.datetime.fromisoformat(iso)) for iso in item.exception_dates]
        calendar_event.add('EXDATE', [d.date() for d in exception_dates] if item.all_day else exception_dates)


def events_to_private_ical_feed(user):
    """
    Generate an ICAL feed for all events associated with the given user.

    :param user: The user to generate an ICAL feed for.
    :return: An ICAL string of all the user's events.
    """
    timezone.activate(ZoneInfo(user.settings.time_zone))

    try:
        calendar = _create_calendar(f"{settings.PROJECT_NAME} Events")

        for event in user.events.prefetch_related('notes_set'):
            calendar_event = _to_vevent(user, event)
            if event.recurrence_rule:
                _add_recurrence(calendar_event, event)
            calendar_event["DESCRIPTION"] = _create_event_description(event)

            calendar.add_component(calendar_event)

        return calendar.to_ical()
    finally:
        timezone.deactivate()


def homework_to_private_ical_feed(user):
    """
    Generate an ICAL feed for all homework associated with the given user.

    :param user: The user to generate an ICAL feed for.
    :return: An ICAL string of all the user's homework.
    """
    timezone.activate(ZoneInfo(user.settings.time_zone))

    try:
        calendar = _create_calendar(f"{settings.PROJECT_NAME} Assignments")

        homework_shown = Homework.objects.for_user(user.pk).filter(course__course_group__shown_on_calendar=True)
        for homework in homework_shown.select_related('category', 'course').prefetch_related('resources', 'notes_set'):
            calendar_event = _to_vevent(user, homework)
            if homework.recurrence_rule:
                _add_recurrence(calendar_event, homework)
            calendar_event["DESCRIPTION"] = _create_homework_description(homework)

            calendar.add_component(calendar_event)

        return calendar.to_ical()
    finally:
        timezone.deactivate()


def courseschedules_to_private_ical_feed(user):
    """
    Generate an ICAL feed for all course schedules associated with the given user.

    The ID given for each event (and thus each VEVENT's UID) is deterministic, derived from the course
    schedule and occurrence, so it is stable across calls.

    :param user: The user to generate an ICAL feed for.
    :return: An ICAL string of all the user's course schedules.
    """
    calendar = _create_calendar(f"{settings.PROJECT_NAME} Class Schedules")

    courses_shown = Course.objects.for_user(user.pk).filter(course_group__shown_on_calendar=True)
    events_by_course = [
        (course, coursescheduleservice.course_schedules_to_events(course, course.schedules))
        for course in courses_shown.select_related('course_group', 'course_group__user',
                                                   'course_group__user__settings').prefetch_related('schedules')
    ]

    timezone.activate(ZoneInfo(user.settings.time_zone))

    try:
        for course, events in events_by_course:
            description = _create_course_schedule_description(course)
            for event in events:
                calendar_event = _to_vevent(user, event)
                calendar_event["DESCRIPTION"] = description

                calendar.add_component(calendar_event)

        return calendar.to_ical()
    finally:
        timezone.deactivate()
