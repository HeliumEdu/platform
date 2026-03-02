__copyright__ = "Copyright (c) 2025 Helium Edu"
__license__ = "MIT"

import logging
from datetime import timezone

import pytz
from dateutil import parser
from django.db.models import Q
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin

from helium.common.views.base import HeliumAPIView

logger = logging.getLogger(__name__)


def _parse_date_param_to_utc(date_str, user_tz_name):
    """
    Parse a date/datetime string and convert to UTC.

    When the input is a date-only string (e.g., "2026-02-02"), it's interpreted
    as midnight in the user's timezone, not the server's timezone. This ensures
    consistent filtering regardless of where the server runs.
    """
    dt = parser.parse(date_str)
    if dt.tzinfo is None:
        # Naive datetime - interpret in user's timezone
        user_tz = pytz.timezone(user_tz_name)
        dt = user_tz.localize(dt)
    return dt.astimezone(timezone.utc)


class HeliumCalendarItemAPIView(HeliumAPIView, ListModelMixin):
    def filter_queryset(self, queryset):
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)

        _from = self.request.query_params.get('from', None)
        to = self.request.query_params.get('to', None)
        if _from and to:
            user_tz_name = self.request.user.settings.time_zone
            _from_raw, to_raw = _from, to
            _from = _parse_date_param_to_utc(_from, user_tz_name)
            to = _parse_date_param_to_utc(to, user_tz_name)
            logger.info(f'[DATE_DEBUG] user_tz={user_tz_name}, from_raw={_from_raw}, to_raw={to_raw}, from_utc={_from}, to_utc={to}')
            queryset = queryset.filter(Q(start__range=(_from, to)) |
                                       Q(end__range=(_from, to)) |
                                       # Also include results where start/end dates are wider than the window
                                       Q(start__lte=_from, end__gte=to))
            logger.info(f'[DATE_DEBUG] queryset count after filter: {queryset.count()}')

        return queryset

    def get(self, request, *args, **kwargs):
        _from = request.query_params.get('from')
        to = request.query_params.get('to')

        if (_from and not to) or (to and not _from):
            raise ValidationError(
                detail="Both 'from' and 'to' must be provided together.",
                code=status.HTTP_400_BAD_REQUEST
            )

        return self.list(request, *args, **kwargs)
