import logging

from django_filters import rest_framework as filters

from helium.planner.models import CourseGroup, Course
from helium.planner.models.basecalendar import BaseCalendar

__author__ = 'Alex Laird'
__copyright__ = 'Copyright 2017, Helium Edu'
__version__ = '1.0.0'

logger = logging.getLogger(__name__)


class BaseCalendarFilter(filters.FilterSet):
    start = filters.IsoDateTimeFilter(name="start", lookup_expr='gte')
    end = filters.IsoDateTimeFilter(name="end", lookup_expr='lte')

    class Meta:
        model = BaseCalendar
        fields = ['start', 'end', ]


class CourseGroupFilter(filters.FilterSet):
    start_date = filters.DateFilter(name="start_date", lookup_expr='gte')
    end_date = filters.DateFilter(name="end_date", lookup_expr='lte')

    class Meta:
        model = CourseGroup
        fields = ['start_date', 'end_date', 'shown_on_calendar', ]


class CourseFilter(filters.FilterSet):
    start_date = filters.DateFilter(name="start_date", lookup_expr='gte')
    end_date = filters.DateFilter(name="end_date", lookup_expr='lte')

    class Meta:
        model = Course
        fields = ['start_date', 'end_date', ]
