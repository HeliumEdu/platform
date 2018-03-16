import datetime
import json
import logging

import pytz
from dateutil import parser
from django.core.cache import cache
from django.utils.timezone import make_aware

from helium.common import enums
from helium.planner.models import Event
from helium.planner.serializers.eventserializer import EventSerializer

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.4.2'

logger = logging.getLogger(__name__)


def _get_start_time_for_weekday(course_schedule, weekday):
    if weekday == 0:
        return course_schedule.sun_start_time
    elif weekday == 1:
        return course_schedule.mon_start_time
    elif weekday == 2:
        return course_schedule.tue_start_time
    elif weekday == 3:
        return course_schedule.wed_start_time
    elif weekday == 4:
        return course_schedule.thu_start_time
    elif weekday == 5:
        return course_schedule.fri_start_time
    elif weekday == 6:
        return course_schedule.sat_start_time


def _get_end_time_for_weekday(course_schedule, weekday):
    if weekday == 0:
        return course_schedule.sun_end_time
    elif weekday == 1:
        return course_schedule.mon_end_time
    elif weekday == 2:
        return course_schedule.tue_end_time
    elif weekday == 3:
        return course_schedule.wed_end_time
    elif weekday == 4:
        return course_schedule.thu_end_time
    elif weekday == 5:
        return course_schedule.fri_end_time
    elif weekday == 6:
        return course_schedule.sat_end_time


def _get_comments(course):
    title = course.title
    if course.website:
        title = "<a href=\"{}\">{}</a>".format(course.website, title)

    if not course.is_online and course.room:
        return "{} in {}".format(title, course.room)
    elif course.website:
        return title
    else:
        return ""


def _get_cache_prefix(course):
    return "{}:{}:courseschedule:".format(course.get_user().pk, course.pk)


def course_schedules_to_events(course, course_schedules):
    """
    For the given course schedule model, generate an event for each class time within the courses's start/end window.

    :param course: The course with a start/end date range to iterate over.
    :param course_schedules: A list of course schedules to generate the events for.
    :return: A list of event resources.
    """
    events = []

    cache_prefix = _get_cache_prefix(course)

    use_cache = False
    cached_keys = cache.keys(cache_prefix + "*") if getattr(cache, "keys", None) else None
    if cached_keys:
        use_cache = True

        for key, event in cache.get_many(cached_keys).items():
            try:
                event = json.loads(event)
                event = Event(id=event['id'],
                              title=event['title'],
                              all_day=event['all_day'],
                              show_end_time=event['show_end_time'],
                              start=parser.parse(event['start']),
                              end=parser.parse(event['end']),
                              owner_id=event['owner_id'],
                              user_id=event['user'],
                              calendar_item_type=event['calendar_item_type'],
                              comments=event['comments'])
                events.append(event)
            except:
                use_cache = False
                events = []

                break

    if not use_cache:
        clear_cache(course, cached_keys)

        day = course.start_date
        while day <= course.end_date:
            for course_schedule in course_schedules.iterator():
                if course_schedule.days_of_week[enums.PYTHON_TO_HELIUM_DAY_OF_WEEK[day.weekday()]] == "1":
                    start_time = _get_start_time_for_weekday(course_schedule,
                                                             enums.PYTHON_TO_HELIUM_DAY_OF_WEEK[day.weekday()])
                    end_time = _get_end_time_for_weekday(course_schedule,
                                                         enums.PYTHON_TO_HELIUM_DAY_OF_WEEK[day.weekday()])
                    start = make_aware(datetime.datetime.combine(day, start_time),
                                       pytz.timezone(course.get_user().settings.time_zone)).astimezone(pytz.utc)
                    end = make_aware(datetime.datetime.combine(day, end_time),
                                     pytz.timezone(course.get_user().settings.time_zone)).astimezone(pytz.utc)
                    comments = _get_comments(course)

                    unique_str = str(course.get_user().pk) + str(
                        course_schedule.pk) + start.isoformat() + end.isoformat()
                    event = Event(id=abs(hash(unique_str)) % (10 ** 8),
                                  title=course.title,
                                  all_day=False,
                                  show_end_time=True,
                                  start=start,
                                  end=end,
                                  owner_id=course.pk,
                                  user=course.get_user(),
                                  calendar_item_type=enums.COURSE,
                                  comments=comments)
                    events.append(event)

                    serializer = EventSerializer(event)
                    cache.set(cache_prefix + str(event.id), json.dumps(serializer.data))

                    break

            day += datetime.timedelta(days=1)

    return events


def clear_cache(course, keys=None):
    if not getattr(cache, "keys", None):
        return

    cache_prefix = _get_cache_prefix(course)
    cached_keys = cache.keys(cache_prefix + "*") if not keys else keys
    for key in cached_keys:
        cache.delete(key)
