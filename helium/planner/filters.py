__copyright__ = "Copyright (c) 2018 Helium Edu"
__license__ = "MIT"
__version__ = "1.5.1"

import logging

from django_filters import rest_framework as filters

from helium.planner.models import CourseGroup, Course, Event, Homework, Reminder

logger = logging.getLogger(__name__)


class EventFilter(filters.FilterSet):
    class Meta:
        model = Event
        fields = {
            'start': ['exact', 'gte'],
            'end': ['exact', 'lt']
        }


class HomeworkFilter(filters.FilterSet):
    class Meta:
        model = Homework
        fields = {
            'start': ['exact', 'gte'],
            'end': ['exact', 'lt'],
            'completed': ['exact'],
            'category': ['exact'],
        }


class CourseGroupFilter(filters.FilterSet):
    class Meta:
        model = CourseGroup
        fields = {
            'shown_on_calendar': ['exact'],
            'start_date': ['exact', 'gte'],
            'end_date': ['exact', 'lte'],
        }


class CourseFilter(filters.FilterSet):
    class Meta:
        model = Course
        fields = {
            'start_date': ['exact', 'gte'],
            'end_date': ['exact', 'lte'],
        }


class ReminderFilter(filters.FilterSet):
    class Meta:
        model = Reminder
        fields = {
            'event': ['exact'],
            'homework': ['exact'],
            'type': ['exact'],
            'sent': ['exact'],
            'start_of_range': ['lte'],
        }
