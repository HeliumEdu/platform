import logging

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2018, Helium Edu'
__version__ = '1.3.0'

logger = logging.getLogger(__name__)


def course_schedule_to_events(course_schedule):
    """
    For the given course schedule model, generate an event for each class time within the courses's start/end window.

    :param course_schedule: The course schedule to generate the events for.
    :return: A list of event resources.
    """
    events = []

    # TODO: implement

    # TODO: responses should, in the future, be cached for at least a few minutes

    return events
