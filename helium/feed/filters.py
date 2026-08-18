__copyright__ = "Copyright (c) Helium Edu"
__license__ = "Apache-2.0"

import django_filters

from helium.feed.models import ExternalCalendar


class ExternalCalendarFilter(django_filters.FilterSet):
    class Meta:
        model = ExternalCalendar
        fields = {
            'shown_on_calendar': ['exact'],
            'updated_at': ['gte'],
        }
