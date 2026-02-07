__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"
__version__ = "1.17.28"

import logging

import django_filters
from django.db.models import Q
from django.utils import timezone

from helium.common.utils.commonutils import split_csv
from helium.planner.models import CourseGroup, Course, Event, Homework, Reminder, Category, Material, MaterialGroup

logger = logging.getLogger(__name__)


class CharInFilter(django_filters.BaseInFilter, django_filters.CharFilter):
    pass


class EventFilter(django_filters.FilterSet):
    class Meta:
        model = Event
        fields = {
            'title': ['exact'],
        }


class HomeworkFilter(django_filters.FilterSet):
    course__id = CharInFilter(field_name='course__id')
    category__id = CharInFilter(field_name='category__id')
    category__title__in = django_filters.CharFilter(method='filter_category_titles')
    shown_on_calendar = django_filters.BooleanFilter(method='filter_shown_on_calendar')
    overdue = django_filters.BooleanFilter(method='filter_overdue')

    class Meta:
        model = Homework
        fields = {
            'id': ['exact'],
            'title': ['exact'],
            'completed': ['exact'],
            'course__id': ['in'],
            'category__id': ['in'],
            'category__title': ['in'],
        }

    def filter_category_titles(self, queryset, name, value):
        return queryset.filter(category__title__in=split_csv(value))

    def filter_shown_on_calendar(self, queryset, name, value):
        return queryset.filter(course__course_group__shown_on_calendar=value)

    def filter_overdue(self, queryset, name, value):
        now = timezone.now()
        if value:
            return queryset.filter(completed=False, start__lt=now)
        else:
            return queryset.filter(
                Q(completed=True) |
                Q(completed=False, start__gte=now)
            )


class CourseGroupFilter(django_filters.FilterSet):
    class Meta:
        model = CourseGroup
        fields = {
            'shown_on_calendar': ['exact'],
            'start_date': ['exact', 'gte'],
            'end_date': ['exact', 'lte'],
            'title': ['exact'],
        }


class CourseFilter(django_filters.FilterSet):
    shown_on_calendar = django_filters.BooleanFilter(method='filter_shown_on_calendar')

    class Meta:
        model = Course
        fields = {
            'start_date': ['exact', 'gte'],
            'end_date': ['exact', 'lte'],
            'title': ['exact']
        }

    def filter_shown_on_calendar(self, queryset, name, value):
        return queryset.filter(course_group__shown_on_calendar=value)


class CategoryFilter(django_filters.FilterSet):
    shown_on_calendar = django_filters.BooleanFilter(method='filter_shown_on_calendar')

    class Meta:
        model = Category
        fields = {
            'course': ['exact'],
            'title': ['exact'],
        }

    def filter_shown_on_calendar(self, queryset, name, value):
        return queryset.filter(course__course_group__shown_on_calendar=value)


class ReminderFilter(django_filters.FilterSet):
    class Meta:
        model = Reminder
        fields = {
            'event': ['exact'],
            'homework': ['exact'],
            'type': ['exact'],
            'sent': ['exact'],
            'dismissed': ['exact'],
            'start_of_range': ['lte'],
            'title': ['exact'],
        }


class MaterialGroupFilter(django_filters.FilterSet):
    class Meta:
        model = MaterialGroup
        fields = {
            'shown_on_calendar': ['exact'],
            'title': ['exact'],
        }


class MaterialFilter(django_filters.FilterSet):
    shown_on_calendar = django_filters.BooleanFilter(method='filter_shown_on_calendar')

    class Meta:
        model = Material
        fields = {
            'title': ['exact'],
        }

    def filter_shown_on_calendar(self, queryset, name, value):
        return queryset.filter(material_group__shown_on_calendar=value)
