__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.11.13"

import logging

from django_filters import rest_framework as filters

from helium.planner.models import CourseGroup, Course, Event, Homework, Reminder, Category, Material, MaterialGroup

logger = logging.getLogger(__name__)


class EventFilter(filters.FilterSet):
    class Meta:
        model = Event
        fields = {
            'start': ['exact', 'gte'],
            'end': ['exact', 'lt'],
            'title': ['exact'],
        }


class HomeworkFilter(filters.FilterSet):
    class Meta:
        model = Homework
        fields = {
            'start': ['exact', 'gte'],
            'end': ['exact', 'lt'],
            'completed': ['exact'],
            'category': ['exact'],
            'title': ['exact'],
        }


class CourseGroupFilter(filters.FilterSet):
    class Meta:
        model = CourseGroup
        fields = {
            'shown_on_calendar': ['exact'],
            'start_date': ['exact', 'gte'],
            'end_date': ['exact', 'lte'],
            'title': ['exact'],
        }


class CourseFilter(filters.FilterSet):
    class Meta:
        model = Course
        fields = {
            'start_date': ['exact', 'gte'],
            'end_date': ['exact', 'lte'],
            'title': ['exact'],
        }


class CategoryFilter(filters.FilterSet):
    class Meta:
        model = Category
        fields = {
            'course': ['exact'],
            'title': ['exact'],
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
            'title': ['exact'],
        }


class MaterialGroupFilter(filters.FilterSet):
    class Meta:
        model = MaterialGroup
        fields = {
            'title': ['exact'],
        }


class MaterialFilter(filters.FilterSet):
    class Meta:
        model = Material
        fields = {
            'title': ['exact'],
        }
