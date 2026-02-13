__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import django_filters

from helium.feed.models import ExternalCalendar


class ExternalCalendarFilter(django_filters.FilterSet):
    class Meta:
        model = ExternalCalendar
        fields = {
            'shown_on_calendar': ['exact'],
            'updated_at': ['gte'],
        }
